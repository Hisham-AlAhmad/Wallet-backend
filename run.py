from app import create_app

app = create_app()


@app.route('/')
def hello():
    return 'Wallet Backend API is Running!'


if __name__ == '__main__':
    app.run(debug=True)
