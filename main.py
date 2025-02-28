from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from sqlmodel import Session, select
from Baghchal import Baghchal
from datetime import timedelta
from MCTS import MCTS
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from models import FriendRequest, FriendRequestCreate, User, UserCreate, UserLogin, UserProfile, create_access_token, create_db_and_tables, get_db, get_password_hash, verify_password

app = FastAPI()


app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

 

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



@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.exec(select(User).where(User.username == user.username)).first()
    if existing_user: 
        raise HTTPException(status_code=400, detail="Username already exits")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"message": "User registered successfully"}


@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.exec(select(User).where(User.username == user.username)).first()
    is_password_verified = verify_password(user.password, db_user.password)
    if not db_user or not is_password_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentails")

    return {"access_token": ""}



@app.get("/get-all-users", response_model=list[UserProfile])
def get_all_users(db: Session = Depends(get_db)):
    users = db.exec(select(User)).all()
    return users


@app.post("/send-friend-request")
def send_friend_request(request: FriendRequestCreate, db: Session = Depends(get_db)):
    friend_request = FriendRequest(sender_id=request.sender_id, receiver_id=request.receiver_id, status="PENDING")
    db.add(friend_request)
    db.commit()
    
    return {"message": "Friend request sent"}


@app.get("/friend-requests/{user_id}")
def get_friend_requests(user_id: int, db: Session = Depends(get_db)):
    friend_requests = db.exec(select(FriendRequest).where(FriendRequest.receiver_id == user_id, FriendRequest.status == "PENDING")).all()
    return friend_requests


@app.post("/respond-friend-request/{request_id}")
def respond_friend_request(request_id: int, response: str,  db: Session = Depends(get_db)):
    friend_request = db.exec(select(FriendRequest).where(FriendRequest.id == request_id)).first()
    if not friend_request: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found")
    
    friend_request.status = response 
    db.commit() 
    
    return {"message": f"Friend request {response}"}



if __name__ == "__main__":
    create_db_and_tables()

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
