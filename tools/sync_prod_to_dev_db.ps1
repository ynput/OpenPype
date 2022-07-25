
<#
.SYNOPSIS
  Helper script to run mongodb.

.DESCRIPTION
  This script will detect mongodb, add it to the PATH and launch it on specified port and db location.

.EXAMPLE

PS> .\run_mongo.ps1

#>

$art = @"

             . .   ..     .    ..
        _oOOP3OPP3Op_. .
     .PPpo~.   ..   ~2p.  ..  ....  .  .
    .Ppo . .pPO3Op.. . O:. . . .
   .3Pp . oP3'. 'P33. . 4 ..   .  .   . .. .  .  .
  .~OP    3PO.  .Op3    : . ..  _____  _____  _____
  .P3O  . oP3oP3O3P' . . .   . /    /./    /./    /
   O3:.   O3p~ .       .:. . ./____/./____/ /____/
   'P .   3p3.  oP3~. ..P:. .  . ..  .   . .. .  .  .
  . ':  . Po'  .Opo'. .3O. .  o[ hacked by hornet ]]]==- - - .  .
    . '_ ..  .    . _OP3..  .  .https://openpype.io.. .
         ~P3.OPPPO3OP~ . ..  .
           .  ' '. .  .. . . . ..  .

"@
Write-Host $art -ForegroundColor DarkGreen

# mongodb port
$port = 2707

# path to database

$dumppath = "T:\scratch\dump"
$proddb = "pype-db"
Write-Host "clearing previous dumps at " -NoNewline
Write-Host $dumppath -ForegroundColor Red
Remove-Item "$dumppath\*" -Recurse -Force


Write-Host "connecting to production database " -NoNewline
Write-Host $proddb -ForegroundColor Cyan -NoNewline
Write-Host " on port " -NoNewline
Write-Host $port -ForegroundColor Yellow
write-Host ""
write-host "dumping and restoring settings - not optional"

mongodump --host $proddb --port $port --out $dumppath --db "openpype"
mongo --host localhost --port 2707 --quiet "openpype" --eval "db.settings.drop();db.logs.drop()"
mongorestore --host localhost --port $port --db openpype T:\scratch\dump\openpype\settings.bson
mongorestore --host localhost --port $port --db openpype T:\scratch\dump\openpype\logs.bson
write-Host "Settings dump Completed" -ForegroundColor Green
Write-Host "starting dialog to pick which collections to merge"

$collections = mongo --host pype-db --port 2707 --quiet "avalon" --eval "db.getCollectionNames().join('\n')"
$collections = $collections | Out-GridView -OutputMode Multiple
foreach ($collection in $collections){
    mongodump --host $proddb --port $port --out $dumppath --db "avalon" --collection $collection
    mongorestore --drop --host localhost --port 2707 --db avalon --collection $collection $dumppath\avalon\$collection.bson
}

write-host "Synced Collections/Projects:"
write-host "--------------------" -ForegroundColor Yellow
Write-Host $collections
write-host "--------------------" -ForegroundColor Yellow
