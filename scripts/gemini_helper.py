import os
import google.generativeai as genai
from PIL import Image

# API Key found in BenchVision
API_KEY = "AIzaSyCxWcdK5UWDIxNurm1X0nRTlbtK-rzBatU"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-3.1-pro-preview')

PROMPT = """
You are an expert hematopathologist. I am providing a microscopic image of a peripheral blood cell from the granulocyte series.
Your task is to classify the cell into one of the following maturation stages:
1. MYELOCYTE: Round/oval nucleus, no indentation.
2. METAMYELOCYTE: Kidney-shaped nucleus, indentation depth < 1/2 of the nucleus width.
3. BAND: C or U-shaped nucleus, indentation depth > 1/2 of the nucleus width.
4. NEUTROPHIL: Lobed nucleus, distinct lobes connected by thin filaments.

Return the result in JSON format:
{
  "label": "STAGE_NAME",
  "confidence": 0.0-1.0,
  "justification": "One sentence reasoning focusing on the nuclear shape."
}
"""

def classify_cell_with_gemini(image_path):
    try:
        img = Image.open(image_path)
        response = model.generate_content([PROMPT, img])
        # Find JSON in response
        text = response.text
        if "{" in text and "}" in text:
            json_str = text[text.find("{"):text.rfind("}")+1]
            import json
            return json.loads(json_str)
        return {"label": "ERROR", "justification": "Could not parse Gemini response"}
    except Exception as e:
        return {"label": "ERROR", "justification": str(e)}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(classify_cell_with_gemini(sys.argv[1]))
