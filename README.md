# vbox
Virtualbox API

Quick setup for testing on Linux:

1. Install Virtualbox - follow directions at https://www.virtualbox.org/wiki/Downloads
2. Clone this repo: `git clone https://github.com/thebluesnevrdie/vbox.git`
3. Install dependencies: `pip install fastapi[all]`
4. Run uvicorn server: `cd vbox/vbox ; uvicorn vboxapi:app`
