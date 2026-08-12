import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from etl_pipeline import generate_customer_segments, generate_fraud_logs

if __name__ == '__main__':
    print('Generating customer_segments...')
    generate_customer_segments()
    print('Generating fraud_logs...')
    generate_fraud_logs()
    print('Generation complete.')
