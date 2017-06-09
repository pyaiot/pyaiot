function initJoystick() {
    var joystick = {
        center: {
            x: 100, // joystick.getClientRects()[0].width / 2
            y: 100  // joystick.getClientRects()[0].height / 2
        },
        active: false,
        timer: null,
        interval: 250, // in milliseconds
    }

    joystick.start = function(node_uid, event) {
        joystick.active = true;
        joystick.active_node = node_uid;
        joystick.move(event);
        joystick.send();
        joystick.timer = window.setInterval(joystick.send, joystick.interval);
    }

    joystick.send = function() {
        var payload = `${joystick.dx}:${joystick.dy}:${joystick.dx+joystick.dy}\n`;
        sendData({
                "uid": joystick.active_node,
                "endpoint": "ribot",
                "payload": payload
            });
    }

    joystick.move = function(event) {
        var offsetX, offsetY;
        if (!joystick.active) return;

        if (event.touches) {
            var target = event.target.getBoundingClientRect();
            offsetX = event.touches[0].clientX - target.left;
            offsetY = event.touches[0].clientY - target.top;
        } else {
            offsetX = event.offsetX;
            offsetY = event.offsetY;
        }

        // normalize
        var deltaMax = Math.min(joystick.center.x, joystick.center.y) * 0.5;
        var deltaX = offsetX - joystick.center.x;
        var deltaY = offsetY - joystick.center.y;
        var delta = Math.sqrt(deltaX*deltaX + deltaY*deltaY);
        if (delta > deltaMax) {
            deltaX *= deltaMax / delta;
            deltaY *= deltaMax / delta;
        }

        joystick.dx = Math.round(deltaX * 255 / deltaMax) * -1
        joystick.dy = Math.round(deltaY * 255 / deltaMax)
        $('.ball').css('transform', `translate(${deltaX}px,${deltaY}px)`);
    }

    joystick.stop = function() {
        if (joystick.active) {
            joystick.active = false;
            joystick.dx = joystick.dy = 0;
            $('.ball').css('transform', `translate(0,0)`);
            window.clearInterval(joystick.timer);
            joystick.send()
        }
    }

    return joystick
}
