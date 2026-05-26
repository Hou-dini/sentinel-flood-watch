import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

def list_models():
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True").lower() == "true"
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
    
    print("=== Environment Configuration ===")
    print(f"GOOGLE_CLOUD_PROJECT: {project}")
    print(f"GOOGLE_CLOUD_LOCATION: {location}")
    print(f"GOOGLE_GENAI_USE_VERTEXAI: {use_vertex}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
    print("=================================\n")
    
    print("Initializing Google GenAI Client...")
    try:
        client = genai.Client()
        
        print("Querying models via SDK...")
        models = client.models.list()
        
        print("\nAvailable Models:")
        count = 0
        for m in models:
            count += 1
            display_name = getattr(m, "display_name", "")
            name = getattr(m, "name", "")
            description = getattr(m, "description", "")
            print(f"{count}. Name: {name}")
            if display_name:
                print(f"   Display Name: {display_name}")
            if description:
                print(f"   Description: {description[:100]}...")
            print("-" * 40)
            
    except Exception as e:
        print(f"\n[ERROR] Failed to list models: {e}")
        print("\nSuggestions for resolving authentication/permissions:")
        print("1. If using Vertex AI (GOOGLE_GENAI_USE_VERTEXAI=True):")
        print("   - Ensure the Vertex AI API (aiplatform.googleapis.com) is enabled in your Google Cloud Console.")
        print("   - Make sure your Service Account has the 'Vertex AI User' role (roles/aiplatform.user) assigned.")
        print("   - Note that Google Cloud Location 'global' might not support end-user model listings; consider changing GOOGLE_CLOUD_LOCATION to 'us-central1' in your .env.")
        print("2. If using Gemini API Studio (GOOGLE_GENAI_USE_VERTEXAI=False):")
        print("   - Ensure GEMINI_API_KEY environment variable is set in your .env file.")

if __name__ == "__main__":
    list_models()
