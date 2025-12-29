from fastapi import APIRouter
import json

get_actions_router = APIRouter()
get_config_router = APIRouter()

@get_actions_router.get("/get_actions")
def get_actions():
    with open("app/actions.json", "r") as f:
        data = json.load(f)
    with open("app/actions.json", "w") as f:
        json.dump([], f)
    return data


@get_config_router.get("/get_config")
def get_config():
    with open("app/config_riego.json", "r") as f:
        data = json.load(f)
    return data

