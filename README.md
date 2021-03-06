# AWSHackathon

## Prerequisites

You'll need the following:

- [Node.js and npm](https://nodejs.org/en/), for the frontend
- [Python 3.5.0+](https://www.python.org/downloads/), for the backend
- [Git](https://git-scm.com/), to clone this repository
- A Browser, to view the website

## Usage

First, clone the git repository:

```bash
$ git clone https://github.com/dreamInCoDeforlife/AWSHackathon.git
```

Then, cd into the repository:

```bash
$ cd AWSHackathon
```

### To setup the backend:

Install all dependencies inside requirements.txt file for python:

```bash
$ pip install -r requirements.txt
```

Launch the four different apps:

```bash
$ python app.py
$ python shipment_app.py
$ python shipped_app.py
$ python complaints.py
```

### To setup the frontend:

cd into the frontend:

```bash
$ cd web
```

Install dependencies:

```bash
$ npm install
```

Build the frontend and launch server:

```bash
$ npm run build
$ npm run start
```

Go to http://localhost:3000/ to view frontend.
