def formatEventStream(eventName: str, data: str):
    return f"event: {eventName}\ndata: {data}\n\n"


async def loremGen():
    while True:
        yield formatEventStream('count', json.dumps([random.randint(1,  20) for i in range(6)]))
        await sleep(2)


@app.get("/count")
async def root() -> StreamingResponse:
    return StreamingResponse(loremGen(), media_type="text/event-stream")
