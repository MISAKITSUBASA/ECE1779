#!/bin/sh
git clone https://BillZou123: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@github.com/xius666/ece1779_A2.git
cd ece1779_A2
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
python run.py