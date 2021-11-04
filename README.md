# Rilevazione di correlazioni tra serie temporali

## Descrizione

Il progetto è costituito da 2 programmi: correlation.py e ntop_host_correlation.py. correlation.py ha lo scopo di ricercare correlazioni tra serie temporali generiche, senza nessun requisito riguardo una loro preclassificazione, mentre ntop_host_correlation.py ricerca correlazioni tra serie temporali rappresentanti host prodotte da ntop, disegnando poi una visualizzazione che sintetizza i risultati ottenuti.

## Installazione e dipendendenze

Le dipendenze necessarie possono essere installate tramite comando:
```
pip3 install -r requirements.txt
```
Nel caso in cui l'installazione di graphviz non vada a buon finde, potrebbe essere necessario installare anche:
```
apt-get install graphviz libgraphviz-dev pkg-config
```
Se non si desidera utilizzare il programma ntop_host_correlation.py, è sufficiente installare il modulo rrdtool tramite comando:
```
pip3 install rrdtool
```

## Parametri
* --input: Parametro obbligatorio, indica il path in cui applicare il programma. Vengono presi in input tutti i file contenuti nel path e nelle sue sottocartelle in modo ricorsivo.
* --known: Parametro flag che indica al programma di correlare solamente serie temporali aventi lo stesso nome. Non è presente in ntop_host_correlation.py in quanto questa funzione è effettuata di default.
* --store: Parametro che indica al programma quanti valori tenere in memoria per calcolare la correlazione continua. Ad esempio, se store è impostato a 60 verranno mantenuti in memoria gli ultimi 60\*2-1 punti. Al raggiungimento di 60\*2 punti, verrà mantenuta solamente la media dei primi 60. Il valore di default è 60. Si ricorda che se il numero di punti disponibili è minore di questo valore, non potrà essere calcolata la correlazione continua. 

## Esecuzione

### correlation.py
Una volta installato il modulo rrdtool, il programma può essere utilizzato su serie temporali salvate in file .rrd o .dat . Nel caso di file .dat, ogni riga deve contenere un valore. Non possono essere dati input file con estensioni non omogenee, ossia possono essere o solo file rrd, o solo file dat.

Il programma può essere avviato tramite il comando:
```
python3 correlation.py --input input_path
```

dove input_path indica la cartella in cui sono situate le serie temporali da analizzare. Il programma cerca ricorsivamente anche nelle sotto cartelle del path indicato, se presenti.

Nel caso in cui si desideri testare il programma correlation.py con le serie temporali generate da ntop, è disponibile uno script avviabile tramite comando:
```
./ntop_test.sh
```
Lo script salva poi i risultati in files .txt seprati per favorire la lettura.
Potrebbe essere necessario avviare lo script con i privilegi di root per leggere la cartella /var/lib/ntopng/2/rrd/.

### ntop_host_correlation.py
Una volta installate le dipendenze, il programma può essere avviato, ad esempio, con comando:
```
python3 ntop_host_correlation.py --input /var/lib/ntopng/2/rrd/ --store 10
```
Anche in questo caso, potrebbe essere necessario avviare il programma con i privilegi di root per leggere la cartella /var/lib/ntopng/2/rrd/.

## Note

All' interno del programma è presente una variabile di debug impostata a 0. Se si desidera avere in output l'elenco di anomalie individuate (indipendentemente dalla correlazione) è necessario settare la variabile ad un valore maggiore di 0.
