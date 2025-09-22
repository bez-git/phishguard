from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import logging
import Core_Machine_Learning_Algorithm as mla  # Import Core_Machine_Learning_Algorithm

# Configure Flask application
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# Load the trained model and feature order from Core_Machine_Learning_Algorithm
try:
    # Assuming `train_rf()` trains or loads the model and returns it
    model = mla.train_rf()
    # Assuming `load_phi_dataset()` or an equivalent function provides feature order
    feature_order = mla.load_feature_order()  # Hypothetical, replace with correct call
except Exception as e:
    logging.error(f"Failed to load the model or feature order: {e}")
    raise


@app.route("/predict", methods=["POST"])
def predict():
    try:
        # Parse JSON input
        data = request.get_json(force=True)

        # Validate the presence of 'features' in the input
        if not data or "features" not in data:
            return jsonify({"error": "Missing 'features' key in JSON"}), 400

        # Extract features from the request
        input_features = data["features"]

        # Create feature vector based on the input format (dictionary or list)
        if isinstance(input_features, dict):  # For dictionary format
            feature_vector = [input_features.get(feat, 0) for feat in feature_order]
        elif isinstance(input_features, list):  # For list format
            if len(input_features) != len(feature_order):
                return jsonify({
                    "error": f"Expected {len(feature_order)} features, got {len(input_features)}"
                }), 400
            feature_vector = input_features
        else:  # Invalid format
            return jsonify({"error": "'features' must be a list or dictionary"}), 400

        # Reshape the feature vector to match the expected input format for the model
        X = np.array(feature_vector).reshape(1, -1)

        # Perform prediction using the loaded model (integrated from Core_Machine_Learning_Algorithm)
        prediction = model.predict(X)[0]
        confidence = float(np.max(model.predict_proba(X)))
        result = "phishing" if prediction == 0 else "legitimate"

        # Log the input and prediction details
        logging.info(f"Input Features: {feature_vector}")
        logging.info(f"Prediction Result: {result}, Confidence: {confidence:.4f}")

        # Return the prediction result as a JSON response
        return jsonify({
            "prediction": result,
            "confidence": round(confidence, 4),
            "features_checked": len(feature_vector)
        })

    except Exception as e:
        logging.error(f"Error during prediction: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Run the Flask server
    app.run(debug=False)