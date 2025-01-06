from fastapi import APIRouter, HTTPException

from ..database import database
from ..functions.auth import authenticateUser, generateToken
from ..models.auth import Response as AuthResponse
from ..models.auth import UserCredentials, Token

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post('/token', response_model=AuthResponse.Token)
async def authenticateCredentials(credentials: UserCredentials,
                                  ):
    """
    Get a token for the user
    :param credentials: The user's credentials. Contains email and password
    :param conn: SQL DB connection

    """

    # Authenticate the user using the given credentials
    user = authenticateUser(database.dbQueue, credentials.email, credentials.password)
    # Return a 401 if the user is not correctly authenticated
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate a JWT token for the user
    token = generateToken(user['id'], user['emailAddress'])

    return AuthResponse.Token(meta={},
                              data=Token(token=token)
                              )

