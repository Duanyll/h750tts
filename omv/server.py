import flask
import base64

# Simple flask server
app = flask.Flask(__name__)

@app.route('/test')
def test():
    return { "code": 0, "message": "success" }

@app.route('/test_post', methods=['POST'])
def test_post():
    # read json data from request
    data = flask.request.json
    print(data)
    return { "code": 0, "message": "success" }

@app.route('/test_upload', methods=['POST'])
def test_upload():
    # { "image": "base64 encoded image" }
    data = flask.request.json
    # decode base64 image
    image = base64.b64decode(data['image'])
    # save image to file
    with open('image.jpg', 'wb') as f:
        f.write(image)
    return { "code": 0, "message": "success" }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)