import gradio as gr
import onnxruntime as ort
import cv2
import numpy as np

# Load zero_dce.onnx
session = ort.InferenceSession("omv/utils/zero_dce.onnx")

# Get input and output names
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

def inference(img):
    # Preprocess the input image
    # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # Pad to times of 32
    h, w, _ = img.shape
    h32 = (h + 31) // 32 * 32
    w32 = (w + 31) // 32 * 32
    img = cv2.resize(img, (w32, h32))
    img = img.transpose(2, 0, 1)
    img = img.astype(np.float32)
    img = img / 255.0
    img = np.expand_dims(img, axis=0)
    
    # Run inference
    outputs = session.run([output_name], {input_name: img})[0]
    outputs = np.squeeze(outputs)
    outputs = outputs.transpose(1, 2, 0)
    outputs = outputs * 255.0
    outputs = outputs.astype(np.uint8)

    # Output grayscale image
    outputs = cv2.cvtColor(outputs, cv2.COLOR_RGB2GRAY)

    # Canny edge detection
    edges = cv2.Canny(outputs, 100, 200)
    
    # Postprocess the output image
    return outputs, edges

image = gr.inputs.Image()
label = gr.outputs.Label('ok')
gr.Interface(fn=inference, inputs=image, outputs=["image", "image"]).launch(debug='True')