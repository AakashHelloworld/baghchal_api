from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from Baghchal import Baghchal
from MCTS import MCTS
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

baghchal = Baghchal()

args = {
    'C': 1.2,
    'num_searches': 1000,
    'max_depth': 10
}
mcts = MCTS(baghchal, args)


class GameState(BaseModel):
    board: list[list[int]]
    tigers: list[list[int]]
    total_goats: int
    goats_on_board: int
    capture_goat: int


@app.get("/")
def read_root():
    return {"message": "Welcome to Baghchal MCTS API"}


@app.post("/get_moves_tiger")
def get_moves_tiger(state: GameState):
    baghchal_info = {
        "tigers": state.tigers,
        "total_goats": state.total_goats,
        "goats_on_board": state.goats_on_board,
        "capture_goat": state.capture_goat
    }

    board = np.array(state.board)
    try:
        mcts_probs = mcts.search(board, baghchal_info, 1)
        
        mcts_probs_array = [[x[0], x[1]] for x in mcts_probs]
        
        return {"moves": mcts_probs_array}
    except Exception as e:
        print("Error:", str(e)) 
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_moves_goat")
def get_moves_goat(state: GameState):
    baghchal_info = {
        "tigers": state.tigers,
        "total_goats": state.total_goats,
        "goats_on_board": state.goats_on_board,
        "capture_goat": state.capture_goat
    }

    board = np.array(state.board)

    try:
        print("Received board:", board)
        print("Baghchal info:", baghchal_info)
        print("Thinking...")
        mcts_probs = mcts.search(board, baghchal_info, -1)
        print("Raw MCTS Output:", mcts_probs)  

        if isinstance(mcts_probs, tuple) and isinstance(mcts_probs[0], int):
            formatted_moves = list(mcts_probs) 

        elif isinstance(mcts_probs, list) or isinstance(mcts_probs, tuple):
            formatted_moves = [list(move) for move in mcts_probs]

        else:
            raise ValueError(f"Unexpected MCTS Output Format: {mcts_probs}")

        print("Formatted Moves:", formatted_moves)
        return {"moves": formatted_moves}

    except Exception as e:
        print("ERROR:", str(e))  
        raise HTTPException(status_code=500, detail=str(e))





if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
