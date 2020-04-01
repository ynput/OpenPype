#!/usr/bin/env python
"""
A Python implementation of rsync

This is a demonstration implementation of the rsync algorithm in Python. It is 
not fast and is not optimised. The primary aim is to provide a simple example
implementation of the algorithm for reference, so code clarity is more important
than performance. Ideas have been liberaly taken from libhsync, xdelta and 
rsync.

     $Id: pysync.py 1.21 Sat, 18 Oct 2003 00:17:54 +1000 abo $
Author  : Donovan Baarda <abo@minkirri.apana.org.au>
License : LGPL
Download: ftp://minkirri.apana.org.au/pub/python

Requires: sys, zlib, types, md4sum
    rollsum (included md4sum-alike rollsum wrapper)

Usage:
    # Low level API signature calculation
    sig=calcsig(oldfile)
    
    # Low level API rsync style incremental delta calc from sig and newdata
    delta=rdeltaobj(sig)
    # or for xdelta style incremental delta calc from oldfile and newdata
    # delta=xdeltaobj(oldfile)
    incdelta=delta.calcdelta(newdata)
      :
    incdelta=delta.flush()

    # Low level API applying incremental delta to oldfile to get newdata
    patch=patchobj(oldfile)
    newdata=patch.calcpatch(incdelta)
      :

    # High level API
    sig=calcsig(oldfile)                        # create a sig object
    delta=calcrdelta(sig,newfile)               # create a rdelta object
    delta=calcxdelta(oldfile,newfile)           # create a xdelta object
    calcpatch(oldfile,delta,newfile)            # apply a delta object

    # File level API
    stats=filesig(oldfile,sigfile)              # create sigfile
    stats=filerdelta(sigfile,newfile,diffile)   # create a rdelta diffile
    stats=filexdelta(oldfile,newfile,diffile)   # create a xdelta diffile
    stats=filepatch(oldfile,diffile,newfile)    # apply a diffile

Where:
    sig         - a signature object
    delta       - a delta object
    stats       - a statistics object that can be printed
    newdata     - the target incremental data sequence
    incdelta    - the incremental delta list
    oldfile     - the source file
    newfile     - the target file
    sigfile     - the signature file
    diffile     - the delta file

a delta is implemented as a list containing a sequence of (context)
compressed insert strings and (offset,length) match pairs. 

A signature is a (length, blocksize, sigtable) tuple, where length and blocksize
are integers. The sigtable is implemented as a rollsum keyed dictionary of
md4sum keyed dictionaries containing offsets.
ie sigtable[rollsum][md4sum]=offset

Note rsync uses md4sums because they are faster than md5sums, but
python doesn't have a built in md4sum wrapper. I use an md4 module
based on the libmd RSA md4 implementation and a modified md5module.c

thoughts on using zlib to compress deltas;

1) compress the whole instruction stream
2) compress the inserts only using Z_SYNC_FLUSH to delimit and put
   inserts into the instruction stream.
3) compress everything using Z_SYNC_FLUSH to delimit boundaries, inserting
   only output for inserts into the instruction stream (rsync?)
4) compress the insert stream without Z_SYNC_FLUSH and put offset/lengths in
   instruction stream, sending compressed inserts seperately (xdelta?)

it depends on how zlib performs with heaps of Z_SYNC_FLUSH's. If it hurts
performance badly, then 4 is best. Otherwise, it would pay to see if zlib
improves compression with inserted context data not included in the output
stream.

My tests on zlib suggest that syncs do hurt a little, but dispite that
including context by compressing _all_ the data, not just the deltas, gives 
the best compression. Unfortunately this has extra load on applying patches 
because it requires all data to be compressed to supply the compression 
stream for the missing context info for decompression.

thoughts on instruction stream;

use fixed length and put only offsets into instruction stream for matches,
put inserts directly into the instruction stream.

use source/offset/length in the instruction stream, and make the inserts a
seperate source (xdelta).

by putting offset/length in the instruction stream rather than just block id's
the instruction stream becomes more generic... anything that can generate 
offset/lengths can generate patches... possibly more optimal ones than rsync
(ie, xdelta's largest possible match type tricks). 

Including a source along with offset/length means multiple sources can be used
for a single patch (like xdelta), though this can be fudged by appending sources
into one long stream.

"""
# psyco is a python accelerator which speeds up pysync by 33%
try:
    import psyco
    psyco.profile()
except:
    pass
from zlib import *
from types import TupleType,StringType
import md4,rollsum

# the default block size used throughout. This is carefuly chosen to try and
# avoid the zlib decompressor sync bug which strikes at about 16K
BLOCK_SIZE=8192

# the various supported flush modes.
R_SYNC_FLUSH=Z_SYNC_FLUSH
R_FINISH=Z_FINISH

def calcsig(oldfile,blocksize=BLOCK_SIZE):
    "Calculates and returns a signature"
    offset=0
    sigtable={}
    data=oldfile.read(blocksize)
    while data:
        sum=md4.new(data).digest()
        sig=rollsum.new(data).digest()
        try:
            sigtable[sig][sum]=offset
        except KeyError:
            sigtable[sig]={}
            sigtable[sig][sum]=offset
        offset=offset+len(data)
        data=oldfile.read(blocksize)
    return (offset,blocksize,sigtable)

class rdeltaobj:
    "Incremental delta calculation class for deltas from signature to newfile"
    def __init__(self,(length,blocksize,sigtable)):
        self.length = length
        self.blocksize = blocksize
        self.sigtable = sigtable
        self.data = ""              # the yet to be processed data
        self.pos = 0                # the position processed up to in data
        self.sig = None             # the rollsum sig of the next data block
        self.last = None            # the last processed delta match/miss
        self.delta = []             # the delta list calculated thus far
        self.comp = compressobj(9)  # the delta zlib compressor object
    def _compress(self):
        "compress and return up to pos, adjusting data and pos"
        data=buffer(self.data,0,self.pos)
        self.data,self.pos=buffer(self.data,self.pos),0
        return self.comp.compress(data)
    def _flush(self,mode=R_SYNC_FLUSH):
        "compress, flush, and return up to pos, adjusting data and pos"
        return self._compress()+self.comp.flush(mode)
    def _findmatch(self):
        "return a match tuple, or raise KeyError if there isn't one"
        # get the rollsum digest, calculating sig if needed
        try:
            sig=self.sig.digest()
        except AttributeError:
            self.sig=rollsum.new(buffer(self.data,self.pos,self.blocksize))
            sig=self.sig.digest()
        # get the matching offset, if it exists, otherwise raise KeyError
        sumtable=self.sigtable[sig]
        sum=md4.new(buffer(self.data,self.pos,self.blocksize))
        return sumtable[sum.digest()],self.sig.count
    def _appendmatch(self,(offset,length)):
        "append a match to delta"
        # if last was a match that can be extended, extend it
        if type(self.last)==TupleType and self.last[0]+self.last[1]==offset:
            self.last=(self.last[0],self.last[1]+length)
        else:
            # else appendflush the last value
            self._appendflush(R_SYNC_FLUSH)
            # make this match the new last
            self.last=(offset,length)
        # increment pos and compress the matched data for context
        self.pos=self.pos+length
        self._compress()
    def _appendmiss(self,length):
        "append a miss to delta"
        if type(self.last)!=StringType:
            # if last was not a miss, appendflush the last value
            self._appendflush(R_SYNC_FLUSH)
            # make this miss the new last
            self.last=""
        # increment pos and compress if greater than blocksize
        self.pos=self.pos+length
        #if self.pos >= self.blocksize:
        #    self.last=self.last+self._compress()
    def _appendflush(self,mode=R_FINISH):
        "append a flush to delta"
        if type(self.last)==StringType:
            self.delta.append(self.last+self._flush(mode))
        elif self.last:
            self.delta.append(self.last)
            self._flush(mode)
        self.last=None
    def calcdelta(self,newdata):
        "incrementaly calculates and returns a delta list"
        self.data=self.data+newdata
        while self.pos+self.blocksize<len(self.data):
            try:
                # append a match, or raise KeyError if there is no match
                self._appendmatch(self._findmatch())
                # clear the rollsum sig
                self.sig = None
            except KeyError:
                # rotate the rollsum sig
                self.sig.rotate(self.data[self.pos],self.data[self.pos+self.blocksize])
                # append the missed byte
                self._appendmiss(1)
        # return and reset the delta
        delta,self.delta=self.delta,[]
        return delta
    def flush(self,mode=R_FINISH):
        "flushes and returns an incremental delta list"
        while self.pos < len(self.data):
            try:
                # append a match, or raise KeyError if there is no match
                self._appendmatch(self._findmatch())
            except KeyError:
                # rollout the first byte
                self.sig.rollout(self.data[self.pos])
                # append the missed byte
                self._appendmiss(1)
        # clear the sig and append a flush to delta
        self.sig = None
        self._appendflush(mode)
        # return and reset the delta
        delta,self.delta=self.delta,[]
        return delta

class xdeltaobj(rdeltaobj):
    "Incremental delta calculation class for deltas from oldfile to newfile"
    # Eventualy this will be replaced with the more optimal xdelta style
    # delta calculation...
    def __init__(self,oldfile,blocksize=512):
        self.oldfile=oldfile
        sigtable={}
        offset,data=0,oldfile.read(blocksize)
        while data:
            sig=rollsum.new(data).digest()
            if not sigtable.has_key(sig):
                sigtable[sig]=offset
            offset,data=offset+len(data),oldfile.read(blocksize)
        rdeltaobj.__init__(self,(offset,blocksize,sigtable))
    def _read(self,offset,length=1):
        self.oldfile.seek(offset)
        return self.oldfile.read(length)
    def _findmatch(self):
        "return a match tuple, or raise KeyError if there isn't one"
        # get the rollsum digest, and calculate sig if needed
        try:
            sig=self.sig.digest()
        except AttributeError:
            sig=self.sig=rollsum.new(buffer(self.data,self.pos,self.blocksize))
            sig=self.sig.digest()
        # get the matching offset, if it exists, otherwise raise KeyError
        offset,length=self.sigtable[sig],0
        # extend the match forwards
        while (self.pos+length<len(self.data) and
               self._read(offset+length)==self.data[self.pos+length]):
            length=length+1
        # if the match was too short, there was no match
        if length<=8:
            raise KeyError
        # extend the match backwards
        while (self.pos and offset and
               self._read(offset-1)==self.data[self.pos-1]):
            self.pos,offset,length=self.pos-1,offset-1,length+1
        # reset last miss if extending backwards removes it
        if self.pos==0 and self.last=="":
            self.last=None
        return offset,length

class patchobj:
    def __init__(self,oldfile):
        self.oldfile=oldfile
        self.cmp=compressobj(9)
        self.out=decompressobj()
        self.newdata=""
    def _appendmatch(self,(offset,length)):
        self.oldfile.seek(offset)
        # read the matched data in chunks
        while length:
            data=oldfile.read(min(length,BLOCK_SIZE))
            self.newdata=self.newdata+data
            # compress the context info and feed it to the decompressor
            self.out.decompress(self.cmp.compress(data))
            length=length-len(data)
        # sync-flush out the compressed context
        self.out.decompress(self.cmp.flush(R_SYNC_FLUSH))
    def _appendmiss(self,insert):
        # decompress the insert data in chunks
        while insert:
            data=self.out.decompress(insert[:BLOCK_SIZE])
            self.newdata=self.newdata+data
            # re-compress the insert data for context info
            self.cmp.compress(data)
            insert=insert[BLOCK_SIZE:]
        # sync_flush the compressor after the insert
        self.cmp.flush(R_SYNC_FLUSH)
    def calcpatch(self,delta):
        for next in delta:
            if type(next)==TupleType:
                self._appendmatch(next)
            else:
                self._appendmiss(next)
        newdata,self.newdata=self.newdata,""
        return newdata
    
def calcrdelta(sig,newfile):
    cmp=rdeltaobj(sig)
    delta, data=[], newfile.read(BLOCK_SIZE)
    while data:
        delta, data = delta+cmp.calcdelta(data), newfile.read(BLOCK_SIZE)
    return delta+cmp.flush()

def calcxdelta(oldfile,newfile):
    cmp=xdeltaobj(oldfile)
    delta, data = [], newfile.read(BLOCK_SIZE)
    while data:
        delta, data = delta+cmp.calcdelta(data), newfile.read(BLOCK_SIZE)
    return delta+cmp.flush()

def calcpatch(oldfile,delta,newfile):
    out=patchobj(oldfile)
    newfile.write(out.calcpatch(delta))

def filesig(oldfile,sigfile,blocksize=BLOCK_SIZE):
    import cPickle
    sig=calcsig(oldfile,blocksize)
    cPickle.dump(sig,sigfile,1)
    return sigstats(sig)
    
def filerdelta(sigfile,newfile,diffile):
    import cPickle
    sig=cPickle.load(sigfile)
    delta=calcrdelta(sig,newfile)
    cPickle.dump(delta,diffile,1)
    return deltastats(delta)
    
def filexdelta(oldfile,newfile,diffile):
    import cPickle
    delta=calcxdelta(oldfile,newfile)
    cPickle.dump(delta,diffile,1)
    return deltastats(delta)

    
def filepatch(oldfile,diffile,newfile):
    import cPickle
    delta=cPickle.load(diffile)
    calcpatch(oldfile,delta,newfile)
    return deltastats(delta)
    
def sigstats((length,blocksize,sigtable)):
    blks = (length+blocksize-1)/blocksize
    rollsumkeys = len(sigtable.keys())
    md4sumkeys = 0
    for v in sigtable.values():
        md4sumkeys = md4sumkeys+len(v)
    return """signature stats
length,size,blocks      : %i %i %i
md4sum keys,collisions  : %i %i
rollsum keys,collisions : %i %i
""" %  (length,blocksize,blks,
        md4sumkeys,blks - md4sumkeys,
        rollsumkeys,blks - rollsumkeys)

def deltastats(delta):
    matches=inserts=match_length=insert_length=0
    for i in delta:
        if type(i)==TupleType:
            matches=matches+1
            match_length=match_length+i[1]
        else:
            inserts=inserts+1
            insert_length=insert_length + len(i)
    return """delta stats
segments: %i
matches : %i %i
inserts : %i %i
""" % (len(delta),matches,match_length,inserts,insert_length)

if __name__ == "__main__":
    import os
    from sys import argv,stdin,stdout,stderr,exit

    def openarg(argno,mode='rb'):
        if (len(argv) <= argno) or (argv[argno] == '-'): 
            if 'r' in mode: return stdin
            return stdout
        return open(argv[argno],mode)
        
    if len(argv)>=2 and argv[1]=="signature":
        oldfile,sigfile=openarg(2,'rb'),openarg(3,'wb')
        stats=filesig(oldfile,sigfile,1024)
        stderr.write(str(stats))
    elif len(argv)>=3 and argv[1]=="rdelta":
        sigfile,newfile,diffile=openarg(2,'rb'),openarg(3,'rb'),openarg(4,'wb')
        stats=filerdelta(sigfile,newfile,diffile)
        stderr.write(str(stats))
    elif len(argv)>=3 and argv[1]=="xdelta":
        oldfile,newfile,diffile=openarg(2,'rb'),openarg(3,'rb'),openarg(4,'wb')
        stats=filexdelta(oldfile,newfile,diffile)
        stderr.write(str(stats))
    elif len(argv)>=3 and argv[1]=="patch":
        oldfile,diffile,newfile=openarg(2,'rb'),openarg(3,'rb'),openarg(4,'wb')
        stats=filepatch(oldfile,diffile,newfile)
        stderr.write(str(stats))
    else:
        print """
Usage:
    %s signature [<oldfile> [<sigfile>]]
    	... generates signature file <sigfile> from <oldfile>
    
    %s rdelta <sigfile> [<newfile> [<diffile>]]
        ... generates rdelta file <diffile> for <newfile> from <sigfile>
        
    %s xdelta <oldfile> [<newfile> [<diffile>]]
        ... generates xdelta file <diffile> for <newfile> from <oldfile>
        
    %s patch <oldfile> [<diffile> [<newfile>]]
        ... applies delta file <diffile> to <oldfile> to generate <newfile>
        
Where file parameters ommitted or specified as '-' indicate standard 
input or output as appropriate.
""" % ((os.path.basename(argv[0]),) * 4)
        exit(1)
