from sqlmodel import SQLModel, create_engine, Session, Field 
from pydantic import BaseModel
import bcrypt
from datetime import timedelta, datetime
import jwt 


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(max_length=20, min_length=5, index=True)
    password: str 
    rating: int = Field(default=0)


class FriendRequest(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    sender_id: int = Field(foreign_key="user.id")
    receiver_id: int = Field(foreign_key="user.id")
    status: str  # PENDING, ACCEPTED, REJECTED  



class Invite(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    inviter: str = Field(foreign_key="user.username")
    invitee: str = Field(foreign_key="user.username")
    inviter_link: str | None = Field(default="")
    invitee_link: str | None = Field(default="")


class FriendRequestCreate(BaseModel):
    receiver_id: int
    sender_id: int


class UserCreate(BaseModel):
    username: str 
    password: str 

class UserLogin(BaseModel):
    username: str 
    password: str 

class UserProfile(BaseModel):
    id: int
    username: str 
    password: str
    rating: int 

    class Config: 
        orm_mode = True


SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///./{sqlite_file_name}"


engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_db(): 
    with Session(engine) as session: 
        yield session


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: timedelta | None = None): 
    to_encode = {
    "data": data.copy(),
    "exp": datetime.now() + (expires_delta or timedelta(minutes=60))
}

    return jwt.encode(to_encode, key="secret", algorithm=ALGORITHM)
    



