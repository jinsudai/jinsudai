import sys
sys.path.insert(0, 'src')
import os

# Vérifier data/processed
if os.path.exists('data/processed'):
    print('data/processed exists')
    files = os.listdir('data/processed')
    print('Files:', files)
else:
    print('data/processed does not exist')

# Vérifier data
if os.path.exists('data'):
    print('data exists')
    dirs = os.listdir('data')
    print('Subdirs:', dirs)
