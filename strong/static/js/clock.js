// 监听主线程中的消息。
// 如果消息中的 command 是 "generate"，则调用 `generatePrimse()`
addEventListener("message", (message) => {
    if (message.data.command === "start") {
        timer = setInterval(f, 1000); 
    }
});

function f(){
    postMessage('next');
}
