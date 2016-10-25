var rp = require('request-promise');
var handlebars = require('handlebars');
var express = require('express');
var coap = require('coap');
var fs = require('fs');
var app = express();

const BROKER_URI = 'http://localhost:8000/nodes'

app.use('/node_modules', express.static(__dirname + '/node_modules'));
app.use('/assets', express.static(__dirname + '/assets'));


// Handlebars helper to pluralize text. Any of these usages work:
//          {{plural numVar 'bagel'}}
//          {{plural numVar 'bagel(s)'}}
//          {{plural numVar 'bagel/bagels'}}
//          bagel{{plural numVar}}
handlebars.registerHelper('plural', function(number, text) {
    var singular = number === 1 || number === 0;
    // If no text parameter was given, just return a conditional s.
    if ( typeof text !== 'string' ) return singular ? '' : 's';
    // Split with regex into group1/group2 or group1(group3)
    var match = text.match( /^([^()\/]+)(?:\/(.+))?(?:\((\w+)\))?/ );
    // If no match, just append a conditional s.
    if ( !match ) return text + ( singular ? '' : 's' );
    // We have a good match, so fire away
    return singular && match[1] // Singular case
        || match[2] // Plural case: 'bagel/bagels' --> bagels
        || match[1] + ( match[3] || 's' ); // Plural case: 'bagel(s)' or 'bagel' --> bagels
});

// console.log(coap.parameters.maxRTT)
// console.log(coap.parameters.maxTransmitSpan)
// console.log(coap.parameters.maxTransmitWait)
// console.log(coap.parameters.ackTimeout)
// console.log(coap.parameters.ackRandomFactor)
// console.log(coap.parameters.maxRetransmit)
// console.log(coap.parameters.maxLatency)
// console.log(coap.parameters.piggybackReplyMs)
// console.log(coap.parameters.exchangeLifetime )

var _nodes = []

var context = {}

var nodecounter = 0

function getNodes() {
    return new Promise(function(resolve, reject) {
        rp({uri: BROKER_URI, json: true })
        .then(function (nodes) {
            // console.log(nodes)
            _nodes = nodes.nodes
            // _nodes = ['2001:470:c87a:abad:5846:257d:3b04:f9d6']
            resolve(_nodes)
        })
        .catch(function (err) {
            console.log(err)
            reject()
        })
    })
}

function getNodeSensors(node) {
    return new Promise(function(resolve, reject) {
        var coapReq = coap.request(`coap://[${node}]/.well-known/core`)

        coapReq.on('response', function(r) {
            console.log(JSON.parse(r.payload.toString()))
            var endpoints = JSON.parse(r.payload.toString())
            
            context[node].board = endpoints.board
            resolve(endpoints.paths)
        })
        coapReq.on('error', function(error) {
            console.log('error', error)
            reject(error)
        })
        coapReq.on('timeout', function(error) {
            console.log('timeout', error)
            reject(error)
        })

        coapReq.end()
    })
}

function getSensorValue(node, sensor) {
    sensor = sensor.substring(1)
    return new Promise(function(resolve, reject) {
        var coapReq = coap.request(`coap://[${node}]/${sensor}`)

        coapReq.on('response', function(r) {
            var value = r.payload.toString()
            if (value == '-') value = '0'
            console.log(value)
            context[node][sensor] = value
            if (sensor == 'led') {
                context[node].ledvalue = parseInt(value)
            }
                
            resolve(value)
        })
        coapReq.on('error', function(error) {
            console.log('error', error)
            reject(error)
        })
        coapReq.on('timeout', function(error) {
            console.log('timeout', error)
            reject(error)
        })

        coapReq.end()
    })
}


function loadTemplate(template) {
    return fs.readFileSync(template + '.html').toString()
}

function sendPage(res) {
    console.log('node done')
    nodecounter++;
    if (nodecounter >= _nodes.length) {
        var c = {}
        c.nodes = []
        _nodes.forEach(node => {
            context[node].ip = node
            c.nodes.push(context[node])
        })
        var html = handlebars.compile(loadTemplate('index'))(c);
        res.send(html);
    }
}

app.get('/', function(req, res) {

    nodecounter = 0

    getNodes().then(nodes => {
        if (nodes.length == 0) {
            sendPage(res)
        }
        nodes.forEach(node => {
            console.log('>>>', node)
            context[node] = {}
            getNodeSensors(node).then(sensors => {
                sensors
                    .filter(e => e.path != '/.well-known/core')
                    .filter(e => e.method == 'GET')

                    //// -> launch coap requests in parallel

                    // .forEach(sensor => {
                    //     // console.log(sensor)
                    //     getSensorValue(node, sensor.path).then(value => {
                    //         // console.log(value)
                    //     })
                    // })

                    //// -> or launch coap requests in sequence

                    .reduce(function(current, next) {
                        return current.then(function() {
                            return getSensorValue(node, next.path);
                        });
                    }, Promise.resolve())
                    .then(
                        function() {
                            
                            console.log('node done')
                            nodecounter++;
                            if (nodecounter >= _nodes.length) {
                                var c = {}
                                c.nodes = []
                                _nodes.forEach(function(node) {
                                    context[node].ip = node
                                    c.nodes.push(context[node])
                                })
                                var html = handlebars.compile(loadTemplate('index'))(c);
                                res.send(html);
                            }
                        }
                    )
                    .catch( 
                        function(err) {
                            console.log(err.stack)
                            res.send('failed')
                        }
                    )

            })
        })
        // nodes.reduce(function(current, next) {
        //     return current.then(function() {
        //         return new Promise(function(resolve, reject) {
        //             context[next] = {}
        //             getNodeSensors(next).then(sensors => {
        //                 sensors
        //                     .filter(e => e.path != '/.well-known/core')
        //                     .filter(e => e.method == 'GET')
        //                     .reduce(function(current, next) {
        //                         return current.then(function() {
        //                             return getSensorValue(node, next.path);
        //                         });
        //                     }, Promise.resolve())
        //                     .then(
        //                         function() {
        //                             console.log('node done')
        //                             resolve()
        //                         }
        //                     )
        //             })
        //         })
        //     })
        // }, Promise.resolve())
        // .then(function() {
        //     console.log('all done')
        // })
            // console.log('all done')
    })

})


app.get('/led/:id', function(req, res) {
    var state = req.query.state
    var coapReq = coap.request({hostname:_nodes[req.params.id], pathname:'/led', method: 'PUT'})
    var payload = state
    coapReq.write(new Buffer(payload))

    coapReq.on('response', function(r) {
        console.log("led")
        // console.log(r.payload.toString())
        res.send('ok')
    })

    coapReq.end()
})


app.listen(8080);

console.log("Web server running at http://[::1]:8080");
