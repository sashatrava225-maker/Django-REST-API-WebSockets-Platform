from pymongo import MongoClient

client = MongoClient(
    "mongodb://root:rootpass@mongo:27017/"
)

db = client["testdb"]

collection = db["users"]

result = collection.insert_one({
    "name": "Iakov",
    "age": 20
})

print(result.inserted_id)
print("Mongo document inserted!")
