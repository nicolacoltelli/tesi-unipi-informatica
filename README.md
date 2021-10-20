# Rilevazione di correlazioni tra serie temporali

## Installazione e dipendendenze

È necessario installare il modulo rrdtool tramite comando:
```
pip3 install rrdtool
```
## Esecuzione

Una volta installato il modulo, il programma può essere utilizzato su serie temporali salvate in file .rrd o .dat . Nel caso di file .dat, ogni riga deve contenere un valore. Non possono essere dati input file con estensioni non omogenee, ossia possono essere o solo file rrd, o solo file dat.

Il programma può essere avviato tramite il comando:
```
python3 correlation.py --input input_path
```

dove input_path indica la cartella in cui sono situate le serie temporali da analizzare. Il programma cerca ricorsivamente anche nelle sotto cartelle del path indicato, se presenti.

Nel caso in cui si desideri testare il programma con le serie temporali generate da ntop, è disponibile uno script avviabile tramite comando:
```
./ntop_test.sh
```
Lo script salva poi i risultati in files .txt seprati per favorire la lettura.
Potrebbe essere necessario avviare lo script con i privilegi di root per leggere la cartella /var/lib/ntopng/2/rrd/.

## Note

All' interno del programma è presente una variabile di debug impostata a 0. Se si desidera avere in output l'elenco di anomalie individuate (indipendentemente dalla correlazione) è necessario settare la variabile ad un valore maggiore di 0.
