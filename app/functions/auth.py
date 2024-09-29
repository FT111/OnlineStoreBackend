import bcrypt
from sqlite3 import Connection
from ..database.databaseQueries import Queries


def authenticateUser(email: str, password: str, dbSession: Connection):
    """
    Authenticates a user by email and password
    """

    user = Queries.Users.getUserByEmail(dbSession, email)

    # Fails if no user is found
    if not user:
        return False

    hashedPassword = user['hashedPassword']
    salt = user['salt']
    password += salt

    # Uses bcrypt to avoid timing attacks
    if bcrypt.checkpw(password.encode('utf-8'), hashedPassword.encode('utf-8')):
        return True
    else:
        return False


