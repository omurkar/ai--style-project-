from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password):
    """
    Convert plain password into a secure password hash.
    """
    return generate_password_hash(password)


def verify_password(password, password_hash):
    """
    Check whether the entered password matches
    the stored password hash.
    """
    return check_password_hash(password_hash, password)