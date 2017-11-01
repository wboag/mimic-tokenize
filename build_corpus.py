
import os, sys
import psycopg2
import pandas as pd
import cPickle as pickle
from collections import defaultdict
import datetime
import re
import random


# organization: data/$pid.txt (order: demographics, outcome, notes)
thisdir = os.path.dirname(os.path.abspath(__file__))
datadir = os.path.join(thisdir, 'data')



def main():

    try:
        size = sys.argv[1]
        if size not in ['small','medium','all']:
            raise Exception('bad')
    except Exception, e:
        print '\n\tusage: python %s <small|medium|all>\n' % sys.argv[0]
        exit(1)

    notes = gather_data(size)

    dump_readable(notes)



def gather_data(size='all'):
    if size == 'small':
        min_id = 0
        max_id = 500
    elif size == 'medium':
        min_id = 0
        max_id = 3000
    elif size == 'all':
        min_id = 0
        max_id = 1e20
    else:
        raise Exception('bad size "%s"' % size)

    # connect to the mimic database
    con = psycopg2.connect(dbname='mimic')

    # Query mimic for notes
    notes_query = \
    """
    select n.subject_id,n.hadm_id,n.text
    from mimiciii.noteevents n
    where iserror IS NULL --this is null in mimic 1.4, rather than empty space
    and subject_id > %d
    and subject_id < %d
    and category = 'Discharge summary'
    and hadm_id IS NOT NULL
    ;
    """ % (min_id,max_id)
    notes = pd.read_sql_query(notes_query, con)

    # notes data
    notes_text = {}
    for i,row in notes.iterrows():
        notes_text[row.subject_id] = row.text

    return notes_text



def dump_readable(X):
    for pid in X:
        filename = os.path.join(datadir, 'readable', '%s.txt' % pid)
        with open(filename, 'w') as f:
            text = X[pid]
            print >>f, text.strip()



if __name__ == '__main__':
    main()
