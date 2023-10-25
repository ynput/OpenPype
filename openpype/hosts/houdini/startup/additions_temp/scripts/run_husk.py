import sys
import math
import os
import subprocess

args = sys.argv
print("args: %s" % (args))

# handle frame ranges
start_index = args.index('-f')
start_frame = int(args[start_index + 1])
print("start_frame: %s" % (start_frame))

end_index = args.index('-e')
end_frame = int(args[end_index + 1])
print("end_frame: %s" % (end_frame))

inc_index = args.index('-i')
inc = int(args[inc_index + 1])
print("inc: %s" % (inc))

chunk_size_index = args.index('-n')
chunk_size = int(args[chunk_size_index + 1])
print("chunk_size: %s" % (chunk_size))

frames = end_frame - start_frame
print("frames: %s" % (frames))

if frames < (inc * (chunk_size - 1)):
    new_chunk_size = frames / float(inc)
    if new_chunk_size.is_integer():
        new_chunk_size += 1
    new_chunk_size = math.floor(new_chunk_size)
    new_chunk_size = max(new_chunk_size, 1)
    print("new_chunk_size: %s" % (new_chunk_size))
    args[chunk_size_index + 1] = str(new_chunk_size)
elif frames == inc * chunk_size:
    new_chunk_size = chunk_size + 1
    print("new_chunk_size: %s" % (new_chunk_size))
    args[chunk_size_index + 1] = str(new_chunk_size)


# handle log path
log_filepath = None
try:
    log_folder_index = args.index('-log')
    log_folder = args[log_folder_index + 1]
    print("log_folder: %s" % (log_folder))

    # check if folder exists
    if not os.path.isdir(log_folder):
        os.makedirs(log_folder)

    log_filepath = os.path.join(log_folder, str(start_frame) + '-' + str(end_frame) + '.txt')
    log_filepath = os.path.normpath(log_filepath).replace('\\', '/')

    # remove file if it exists
    if os.path.isfile(log_filepath):
        os.remove(log_filepath)

    print("log_folder: %s" % (log_filepath))
    args.remove(log_folder)
    args.remove('-log')
except Exception as e:
    print(e)


# remove last two items, the end frame
del args[end_index]
del args[end_index]

# remove first item, python script
del args[0]


command = ' '.join(args)
print("command: %s" % (command))

if log_filepath:
    print('start logging')
    with open(log_filepath, 'a') as f:
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True) as p:
            for line in p.stdout:
                f.write(line)
                print(line)

            for line in p.stderr:
                f.write(line)
                print(line)
else:
    print('no logging')
    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True) as p:
        for line in p.stdout:
            print(line)

        for line in p.stderr:
            print(line)

rc = p.returncode
print('return code: ' + str(rc))

#if rc != 0:
#    raise ValueError('Husk didnt finish succesfully')
