# filename: list_gemini_models.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

print("Attempting to list available Gemini models...")

try:
    # Load the .env file from the configs directory
    env_path = os.path.join(os.path.dirname(__file__), 'configs', '.env')
    if not os.path.exists(env_path):
        print(f"Error: .env file not found at {env_path}")
        print("Please make sure you are running this from the root RepoMaster directory.")
    else:
        load_dotenv(env_path)

        # Get the API key
        api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
            print("Error: GEMINI_API_KEY not found in .env file.")
        else:
            # Configure the client
            genai.configure(api_key=api_key)

            print("\n--- Available Models ---")

            # Call the ListModels function
            for model in genai.list_models():
                # Check if the model supports the 'generateContent' method
                if 'generateContent' in model.supported_generation_methods:
                    print(f"✅ Model: {model.name}")
                    print(f"   - Supports: {model.supported_generation_methods}\n")
                else:
                    print(f"❌ Model: {model.name}")
                    print(f"   - (Does NOT support 'generateContent')\n")

            print("--------------------------")
            print("\nAction: Copy a model name marked with ✅ (e.g., 'models/gemini-1.5-pro-latest')")
            print("and paste it into your 'configs/.env' file as the value for 'GEMINI_MODEL'.")

except ImportError:
    print("\nError: The 'google-generativeai' or 'python-dotenv' package is not installed.")
    print("Please install them in your 'repomaster' environment:")
    print("pip install google-generativeai python-dotenv")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")