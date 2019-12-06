from tensorflow.python.compiler.tensorrt import trt_convert as trt
import tensorflow as tf


converter = trt.TrtGraphConverterV2(
    input_saved_model_dir="models/model_v5")
converter.convert()
converter.save("models/model_v5_trt")