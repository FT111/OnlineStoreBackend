from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json, uvicorn, random
from asyncio import sleep

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

lorem = '''Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam vitae magna a nibh dictum euismod. Nam lorem massa, euismod sed magna id, hendrerit faucibus risus. Morbi condimentum consectetur blandit. Aliquam pretium convallis turpis, non varius nulla lobortis quis. Curabitur purus ex, faucibus eget scelerisque quis, mollis id diam. Donec eu venenatis massa. Proin vitae massa orci. Sed feugiat sodales elit, ut tempor erat vehicula vel. Vivamus vitae sem purus. Nulla eu eros rhoncus, ullamcorper odio non, pulvinar lorem. Nullam ut dolor commodo, lobortis urna at, eleifend nulla. Nunc placerat mi erat, vel gravida massa pretium non. Proin vulputate nulla lectus, in dignissim orci euismod vitae.

Vestibulum eu dui vel ligula tincidunt tincidunt. Quisque nunc urna, vulputate ut neque at, porttitor gravida elit. Aliquam a varius orci, ac placerat enim. Nam dapibus lobortis rutrum. Pellentesque consequat tellus id posuere aliquet. Sed porttitor, neque congue facilisis efficitur, ex tellus hendrerit sapien, non elementum lorem nisl nec velit. Praesent eu turpis sem. Mauris molestie venenatis sem, nec tincidunt lectus dictum at.

Ut in consequat mauris, eu ullamcorper libero. Pellentesque risus metus, accumsan tristique consectetur sagittis, ornare ut enim. Vivamus luctus tempor est, vel ultricies metus laoreet eget. Donec eget justo imperdiet, dignissim ex sed, gravida velit. Sed posuere neque eu lacus pretium maximus. Sed vulputate, libero a lacinia sagittis, metus metus semper metus, in iaculis massa tortor nec nibh. Sed est dui, fringilla at volutpat sed, hendrerit sed nisl. Ut tempor diam sed nulla tempor mattis. Mauris nulla nunc, ornare ut pellentesque vel, placerat sed arcu. Curabitur ultricies augue eget odio ultricies, in consectetur lacus aliquet. Sed pulvinar ultricies purus. Etiam efficitur risus vel nisl accumsan, at sollicitudin purus porta.

Vivamus sodales nibh in leo sodales, sit amet hendrerit augue egestas. Duis in erat sollicitudin, lobortis justo nec, tincidunt nisi. Donec maximus arcu non magna viverra, sed vestibulum mauris eleifend. Fusce condimentum ut eros a gravida. Aliquam a orci aliquam, luctus elit sed, lacinia nibh. Donec viverra enim fermentum varius tempor. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Cras sed bibendum est. Donec tincidunt mollis accumsan. Phasellus maximus quis leo at efficitur. Aenean elit mauris, pulvinar nec quam nec, suscipit varius ante. Phasellus orci dolor, sollicitudin id massa non, congue ultrices justo.

Proin suscipit aliquet ornare. Mauris nec ullamcorper purus. Ut congue a odio placerat ultrices. Vivamus ac molestie felis. Ut iaculis, tellus non consequat auctor, ligula arcu finibus lacus, vitae aliquam neque mauris non diam. Sed posuere varius orci, quis commodo mauris vulputate eu. Praesent sagittis arcu vitae massa porta venenatis. Ut porta molestie metus eu pharetra. Nullam facilisis mauris aliquam dignissim tempus. Integer sed lacus faucibus, efficitur nisi sit amet, interdum sapien. Nullam sit amet dolor eu lectus rhoncus viverra. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Maecenas nec sem arcu. Fusce vel blandit leo, a dictum leo. Nulla tincidunt est interdum odio scelerisque malesuada. Morbi id ex sapien.'''


def formatEventStream(eventName: str, data: str):
    return f"event: {eventName}\ndata: {data}\n\n"


async def loremGen():
    for word in lorem.split():
        yield formatEventStream("count", word)
        await sleep(1)


@app.get("/count")
async def root():
    return StreamingResponse(loremGen(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
