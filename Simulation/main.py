from simulate import WQSession
from fastapi import FastAPI, BackgroundTasks
from schemas import Alpha
from math import ceil
import os
import traceback

credfiles = []

for file in os.listdir("creds"):
    if file.endswith(".json"):
        credfiles.append(f"creds/{file}")

sessions = [
    WQSession(json_fn=file) for file in credfiles if not file.endswith("example.json")
]

def chunk_into_n(lst, n):
    if n <= 0:
        return [lst]
    size = ceil(len(lst) / n)
    return list(map(lambda x: lst[x * size : x * size + size], list(range(n))))

def simulate_all(data: list[Alpha]):
    global sessions
    
    try:
        if not sessions:
            print("CRITICAL: No valid WQSession configurations found in creds folder.")
            return

        data_chunks = chunk_into_n(data, len(sessions))

        # Assign each chunk of data to a WQSession
        for i, session in enumerate(sessions):
            if i >= len(data_chunks) or not data_chunks[i]:
                print(f"Session {i} has no alphas assigned. Skipping.")
                continue

            print(f"Simulating for session {i}...")
            
            # SANITIZATION LAYER: Convert Pydantic schemas and nested Enums into clean primitive JSON
            chunk = []
            for alpha_item in data_chunks[i]:
                if hasattr(alpha_item, "model_dump"):
                    # Pydantic v2 optimization
                    clean_dict = alpha_item.model_dump(mode="json")
                elif hasattr(alpha_item, "dict"):
                    # Pydantic v1 fallback
                    clean_dict = alpha_item.dict()
                    clean_dict = {k: (v.value if hasattr(v, "value") else v) for k, v in clean_dict.items()}
                else:
                    clean_dict = dict(alpha_item)
                    clean_dict = {k: (v.value if hasattr(v, "value") else v) for k, v in clean_dict.items()}
                
                chunk.append(clean_dict)

            print(f"Sanitized payload for session {i} ready:")
            print(chunk)
            
            # Execute simulation with clean primitive types
            session.simulate(chunk)
            print(f"Session {i} simulation payload successfully transmitted to WorldQuant API.")

    except Exception as background_error:
        print("\n" + "="*60)
        print("CRITICAL ERROR ENCOUNTERED IN BACKGROUND TASK")
        print("="*60)
        traceback.print_exc()
        print("="*60 + "\n")

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/add_alphas")
def add_simulate(alphas: list[Alpha], bgt: BackgroundTasks):
    bgt.add_task(simulate_all, alphas)
    return {"status": "Added to queue!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
