function print_ws_close_reason(code) {
    var reason;
    // See http://tools.ietf.org/html/rfc6455#section-7.4.1
    switch(code) {
    case 1000:
        reason = "Normal closure, meaning that the purpose for which the\
                  connection was established has been fulfilled.";
        break
    case 1001:
        reason = "An endpoint is \"going away\", such as a server going down\
                  or a browser having navigated away from a page.";
        break
    case 1002:
        reason = "An endpoint is terminating the connection due to a protocol\
                  error";
        break
    case 1003:
        reason = "An endpoint is terminating the connection because it has\
                  received a type of data it cannot accept (e.g., an endpoint\
                  that understands only text data MAY send this if it receives\
                  a binary message).";
        break
    case 1004:
        reason = "Reserved. The specific meaning might be defined in the\
                  future.";
        break
    case 1005:
        reason = "No status code was actually present.";
        break
    case 1006:
       reason = "The connection was closed abnormally, e.g., without sending\
                 or receiving a Close control frame";
        break
    case 1007:
        reason = "An endpoint is terminating the connection because it has\
                  received data within a message that was not consistent with\
                  the type of the message (e.g., non-UTF-8\
                  [http://tools.ietf.org/html/rfc3629] data within a text\
                  message).";
        break
    case 1008:
        reason = "An endpoint is terminating the connection because it has\
                  received a message that \"violates its policy\". This\
                  reason is given either if there is no other sutible\
                  reason, or if there is a need to hide specific details\
                  about the policy.";
        break
    case 1009:
       reason = "An endpoint is terminating the connection because it has\
                 received a message that is too big for it to process.";
        break
    case 1010:
        // Note that this status code is not used by the server,
        // because it can fail the WebSocket handshake instead.
        reason = "An endpoint (client) is terminating the connection because\
                  it has expected the server to negotiate one or more\
                  extension, but the server didn't return them in the\
                  response message of the WebSocket handshake.";
        break
    case 1011:
        reason = "A server is terminating the connection because it\
                  encountered an unexpected condition that prevented it\
                  from fulfilling the request.";
        break
    case 1015:
        reason = "The connection was closed due to a failure to perform a\
                  TLS handshake (e.g., the server certificate can't be\
                  verified).";
        break
    default:
        reason = "Unknown reason";
    }
    console.log("Code: ", code, "\nReason:", reason)
}
