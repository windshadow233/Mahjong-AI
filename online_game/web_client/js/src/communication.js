let ws;
let buffer = "";
let intervalId;

function send(data){
    const buffer = new TextEncoder().encode(JSON.stringify(data) + '\n');
    ws.send(buffer);
}

window.addEventListener("beforeunload", function(event) {
    send({event: 'quit'});
});
window.onload = () => {
    document.getElementById("host").value = window.location.hostname;
}

function processBuffer(){
    const newlineIndex = buffer.indexOf("\n");
    if (newlineIndex !== -1){
        const message = buffer.substring(0, newlineIndex);
        buffer = buffer.substring(newlineIndex + 1);
        try {
            const data = JSON.parse(message);
            handleMessage(data);
        } catch (e) {
            console.log('解析JSON失败:', e);
        }
    }
}

function connectWebSocket() {
    const host = document.getElementById("host").value || window.location.hostname;
    const port = document.getElementById("port").value || '8888';
    const usernameInput = document.getElementById("username");
    const username = usernameInput.value;
    let observe;
    if (!username) {
        alert("请输入用户名");
        return
    }
    const observerModeCheckbox = document.getElementById('observerMode');
    observe = observerModeCheckbox.checked;
    try {
        const protocol = window.location.protocol;
        if (protocol === 'https:') {
            ws = new WebSocket('wss://' + host + ':' + port);
        } else {
            ws = new WebSocket('ws://' + host + ':' + port);
        }
    } catch (error){
        alert(error);
    }

    ws.addEventListener('open', function(event) {
        console.log('WebSocket connection opened:', event);

        intervalId = setInterval(function() {
            if (buffer.length > 0) {
                processBuffer();
            }
        }, 50);

        const data = {
            'username': username,
            'observe': observe
        };
        send(data);
    });

    ws.addEventListener('message', function(event) {
        const reader = new FileReader();

        reader.onload = function() {
            const text = reader.result;
            buffer += text;
        };

        reader.readAsText(event.data);
    });

    ws.addEventListener('close', function(event) {
        console.log('WebSocket connection closed:', event);
        clearInterval(intervalId);
    });

    ws.addEventListener('error', function(event) {
        console.log('WebSocket error:', event);
        alert("已断开连接");
    });
}

let gameObj = {
    username: null,
    seat: null,
    machi: [],
    _furiten: false,
    oya: null,
    _game_round: null,
    honba: null,
    _riichi_ba: null,
    _dora_indicator: [],
    _agents: [],
    _left_num: null,
    _tiles: [],
    furo: {},
    furo_count: 0,
    observe: false,
    game_start: false,
    end: false
}

Object.defineProperties(gameObj, {
    'tiles': {
        get: function () {
            return this._tiles
        },
        set: function (value) {
            this._tiles = value;
            this._tiles.sort((a, b) => a - b);
            scene.renderHand(this._tiles)
        }
    },
    'furiten': {
        get: function () {
            return this._furiten;
        },
        set: function (value) {
            this._furiten = value;
            scene.renderFuriten(value);
        }
    },
    'game_round': {
        get: function () {
            return this._game_round;
        },
        set: function (value) {
            this._game_round = value;
            this.oya = value % 4;
        }
    },
    'riichi_ba': {
        get: function () {
            return this._riichi_ba;
        },
        set: function (value) {
            this._riichi_ba = value;
            scene.renderRiichiBa(value);
        }
    },
    'dora_indicator': {
        get: function () {
            return this._dora_indicator;
        },
        set: function (value) {
            this._dora_indicator = value;
            scene.renderDora(value);
        }
    },
    'agents': {
        get: function () {
            return this._agents;
        },
        set: function (value) {
            this._agents = value;
            for (let i = 0; i < 4; i ++) {
                let agent = value[i];
                scene.renderPlayerInfo(this.seat, i, agent['username'], agent['score'] * 100, this.oya, this.observe);
                scene.renderRiver(this.seat, i, agent['river'], agent['riichi_tile']);
            }
        }
    },
    'left_num': {
        get: function () {
            return this._left_num;
        },
        set: function (value) {
            this._left_num = value;
            scene.renderLeftTileCount(value);
        }
    }
})

function handleStart(message) {
    const gameInfo = message['game']
    const selfInfo = message['self']

    scene.renderGameInfo(gameInfo['round'], gameInfo['honba']);
    scene.renderLeftTileCount(gameInfo['left_num']);
    gameObj.username = selfInfo['username'];
    gameObj.seat = selfInfo['seat'];
    gameObj.tiles = selfInfo['tiles'];
    gameObj.furo = selfInfo['furo'];
    gameObj.furo_count = selfInfo['furo_count'];
    gameObj.machi = selfInfo['machi'];
    gameObj.end = false;
    gameObj.furiten = false;
    gameObj.game_round = gameInfo['round'];
    gameObj.honba = gameInfo['honba'];
    gameObj.riichi_ba = gameInfo['riichi_ba'];
    gameObj.dora_indicator = gameInfo['dora_indicator'];
    gameObj.agents = gameInfo['agents'];
    gameObj.left_num = gameInfo['left_num'];
    gameObj.game_start = true;

    scene.renderRightHand(gameObj.agents[(gameObj.seat + 1) % 4]['tile_count']);
    scene.renderOppoHand(gameObj.agents[(gameObj.seat + 2) % 4]['tile_count']);
    scene.renderLeftHand(gameObj.agents[(gameObj.seat + 3) % 4]['tile_count']);
    for (let i = 0; i < 4; i++) {
        scene.renderFuros(gameObj.seat, i, gameObj.agents[i]['furo'], gameObj.agents[i]['kui_info']);
    }
}

function handleDraw(message) {
    let tile_id = message['tile_id']
    let who = message['who']
    scene.toggleBlink(mod(who - gameObj.seat, 4));
    gameObj.agents[who]['tile_count'] += 1;
    if (tile_id !== undefined) {
        gameObj.tiles.push(tile_id);
        scene.renderDraw(who, who, tile_id);
    } else {
        scene.renderDraw(gameObj.seat, who);
    }
}

function handleDiscard(message) {
    let who = message['who'];
    let tileId = message['tile_id'];
    let handDiscard = !message['mode'];
    let isRiichi = message['is_riichi'];
    gameObj.agents[who]['discard'].push(tileId);
    gameObj.agents[who]['tile_count'] -= 1;
    if (who === gameObj.seat) {
        if (gameObj.observe) {
            let idx = gameObj.tiles.indexOf(tileId);
            scene.renderDiscard(gameObj.seat, who, tileId, idx, isRiichi);
            gameObj.tiles.splice(idx, 1);
            gameObj.tiles.sort((a, b) => a - b);
            scene.time.delayedCall(800, () => {
                scene.renderHand(gameObj.tiles);
            });
        }
    } else {
        let relativePos = mod(who - gameObj.seat, 4);
        let idx = handDiscard?null:-1;
        scene.renderDiscard(gameObj.seat, who, tileId, idx, isRiichi);
        switch (relativePos) {
            case 1:
                scene.time.delayedCall(800, () => {
                    scene.renderRightHand(gameObj.agents[who]['tile_count']);
                });
                break
            case 2:
                scene.time.delayedCall(800, () => {
                    scene.renderOppoHand(gameObj.agents[who]['tile_count']);
                });
                break
            case 3:
                scene.time.delayedCall(800, () => {
                    scene.renderLeftHand(gameObj.agents[who]['tile_count']);
                });
                break
        }
    }
}

function handleFuro(message) {
    let event = message['event'];
    let action = message['action'];
    let pattern = action['pattern'];
    let kuiTile = action['kui']
    let who = action['who'];
    scene.toggleBlink(mod(who - gameObj.seat, 4));
    let fromWho = action['from_who'];
    let furoType, kanType, add;
    let tileSet;
    let kuiX, kuiY;
    switch (event) {
        case 'chi':
            scene.renderAction(gameObj.seat, who, '吃', gameObj.agents[who]['is_ai']);
            gameObj.agents[who]['tile_count'] -= 2;
            tileSet = new Set(pattern);
            [kuiX, kuiY] = scene.popFromRiver(fromWho);
            furoType = 0;
            break
        case 'pon':
            scene.renderAction(gameObj.seat, who, '碰', gameObj.agents[who]['is_ai']);
            gameObj.agents[who]['tile_count'] -= 2;
            tileSet = new Set(pattern);
            [kuiX, kuiY] = scene.popFromRiver(fromWho);
            furoType = 1;
            break
        case 'kan':
            [kanType, pattern, add] = pattern;
            tileSet = new Set([pattern * 4, pattern * 4 + 1, pattern * 4 + 2, pattern * 4 + 3]);
            switch (kanType) {
                case 0:
                    scene.renderAction(gameObj.seat, who, '杠', gameObj.agents[who]['is_ai']);
                    gameObj.agents[who]['tile_count'] -= 4;
                    furoType = 3;
                    break
                case 1:
                    scene.renderAction(gameObj.seat, who, '杠', gameObj.agents[who]['is_ai']);
                    gameObj.agents[who]['tile_count'] -= 3;
                    [kuiX, kuiY] = scene.popFromRiver(fromWho);
                    furoType = 2;
                    break
                case 2:
                    //加杠行为去下面的代码里处理
                    return;
            }
            break
        case 'addkan':
            [kanType, pattern, add] = pattern;
            tileSet = new Set([add]);
            scene.renderAction(gameObj.seat, who, '杠', gameObj.agents[who]['is_ai']);
            gameObj.agents[who]['tile_count'] -= 1;
            furoType = 3;
            break
    }
    if (kanType !== 2){
        scene.addFuro(gameObj.seat, who, furoType, Array.from(tileSet), kuiTile, fromWho, kuiX, kuiY);
    } else {
        scene.addKan(gameObj.seat, who, pattern, add);
    }
    let handLen = gameObj.agents[who]['tile_count'];
    let relativePos = mod(who - gameObj.seat, 4);
    switch (relativePos) {
        case 0:
            gameObj.tiles = gameObj._tiles.filter(x => !tileSet.has(x));
            break
        case 1:
            scene.renderRightHand(handLen);
            break
        case 2:
            scene.renderOppoHand(handLen);
            break
        case 3:
            scene.renderLeftHand(handLen);
    }
}

function handleRiichi(message) {
    let action = message['action'];
    let who = action['who'];
    let step = action['step'];
    let wRiichi = action['double_riichi'];
    let p = gameObj.agents[who];
    if (step === 1) {
        p['riichi'] = 1;
        p['riichi_round'] = p['discard'].length + 1;
        if (wRiichi) {
            scene.renderAction(gameObj.seat, who, 'w立直', gameObj.agents[who]['is_ai']);
        } else {
            scene.renderAction(gameObj.seat, who, '立直', gameObj.agents[who]['is_ai']);
        }
    } else {
        p['score'] -= 10;
        gameObj.riichi_ba += 1;
        scene.renderPlayerInfo(gameObj.seat, who, p['username'], p['score'] * 100, gameObj.oya, gameObj.observe);
    }
}

function handleAgari(message) {
    let actions = message['action'];
    for (let action of actions) {
        let who = action['who'];
        let fromWho = action['from_who'];
        let machi = action['machi'];
        let hai = action['hai'];
        hai.splice(hai.indexOf(machi), 1);
        let tsumo;
        if (who === fromWho) {
            tsumo = true;
            scene.renderAction(gameObj.seat, who, '自摸', gameObj.agents[who]['is_ai']);
            hai.push(machi);
        } else {
            tsumo = false;
            scene.renderAction(gameObj.seat, who, '荣', gameObj.agents[who]['is_ai']);
        }
        if (who !== gameObj.seat){
            scene.time.delayedCall(1000, () => {
                scene.renderOthersOpenHand(gameObj.seat, who, hai, tsumo);
            })
        }
    }
}

function handleRyuukyoku(message) {
    let why = message['why'];
    switch (why) {
        case 'ron3':
            let actions = message['action'];
            for (let action of actions) {
                let who = action['who'];
                let hai = action['hai'];
                scene.renderAction(gameObj.seat, who, '荣', gameObj.agents[who]['is_ai']);
                if (who !== gameObj.seat) {
                    scene.time.delayedCall(1000, () => {
                        scene.renderOthersOpenHand(gameObj.seat, who, hai, false);
                    });
                }
            }
            break
        case 'yao9':
            let who = message['who'];
            let hai = message['hai'];
            hai.sort((a, b) => a - b);
            if (who !== gameObj.seat){
                scene.time.delayedCall(1000, () => {
                    scene.renderOthersOpenHand(gameObj.seat, who, hai, true);
                });
            }
            break
        case 'yama_end':
            let machiPlayers = message['machi_state'];
            let noMachi = [0, 1, 2, 3].filter(key => !machiPlayers.hasOwnProperty(key.toString()));
            scene.time.delayedCall(1000, () => {
                Object.entries(machiPlayers).forEach(([key, value]) => {
                    let hai = value[0];
                    hai.sort((a, b) => a - b);
                    let who = parseInt(key);
                    if (who !== gameObj.seat){
                        scene.renderOthersOpenHand(gameObj.seat, who, hai, false);
                    }
                });

                noMachi.forEach((who) => {
                    if (who !== gameObj.seat){
                        scene.renderOthersOpenHand(gameObj.seat, who, gameObj.agents[who]['tile_count']);
                    }
                });
            });
            break
    }
}

function handleSettlement(message) {
    let res = message['res'];
    let scoreDelta = message['score'];
    let userInfo = gameObj.agents.map((item) => {return [item['username'], item['score']];});
    if (Array.isArray(res)) {
        scene.renderAgari(gameObj.seat, gameObj.oya, res, gameObj.dora_indicator, message['ura_dora'], userInfo, scoreDelta, gameObj.observe);
    } else {
        scene.renderRyuukyoku(gameObj.seat, gameObj.oya, res, userInfo, scoreDelta, gameObj.observe);
    }
}

async function FetchDecision() {
    return await scene.queue.dequeue();
}

function handleSelectTile(message) {
    if (!gameObj.observe) {
        let riichi = message['riichi'];
        let banned = message['banned'];
        let tiles = message['tiles'];
        let isRiichi = message['is_riichi_tile'];
        if (tiles === 'all') {
            tiles = gameObj.tiles;
        } else {

        }
        if (riichi) {
            setTimeout(() => {
                const tileId = gameObj.tiles.splice(-1, 1)[0];
                send({'event': 'discard', 'tile_id': tileId});
                scene.renderDiscard(gameObj.seat, gameObj.seat, tileId, -1, isRiichi);
                gameObj.tiles.sort((a, b) => a - b);
                scene.time.delayedCall(800, () => {
                    scene.renderHand(gameObj.tiles);
                });
            }, 1500);
            return;
        }
        scene.selectTile = true;
        FetchDecision().then(idx => {
            const tileId = gameObj.tiles[idx];
            if (!tiles.includes(tileId)) {
                alert('请选择合理的立直宣言牌');
                handleMessage(message);
                return;
            }
            if (banned.includes(Math.floor(tileId / 4))) {
                alert('禁止筋、现物食替行为');
                handleMessage(message);
                return;
            }
            gameObj.tiles.splice(idx, 1);
            send({'event': 'discard', 'tile_id': tileId});
            scene.renderDiscard(gameObj.seat, gameObj.seat, tileId, idx, isRiichi);
            gameObj.tiles.sort((a, b) => a - b);
            scene.time.delayedCall(800, () => {
                scene.renderHand(gameObj.tiles);
            });
        });
    }
}

function handleDecision(message) {
    if (gameObj.observe) {

    } else {
        let actions = message['actions'];
        scene.renderDecisions(actions);
        FetchDecision().then(action => {
           send({'event': 'decision', 'action': action});
        });
    }
}

function handleScore(message) {
    let value = message['score'];
    let usernames = gameObj.agents.map(item => {return item['username'];});
    scene.renderFinalScore(usernames, value, gameObj.observe);
}

function handleMessage(message) {
    // console.log(message);
    const event = message['event'] || '';
    switch (event){
        case 'join':
            const status = message['status'];
            if (status !== 0){
                scene.setWsFcn(send);
                document.getElementById("connecting-form").style.display = 'none';
            }
            if (status === -1){
                gameObj.observe = true;
            }
            alert(message['message']);
            break
        case 'start':
            handleStart(message);
            break
        case 'update':
            const key = message['key'];
            const value = message['value'];
            gameObj[key] = value;
            break
        case 'draw':
            handleDraw(message);
            break
        case 'discard':
            handleDiscard(message);
            break
        case 'chi':
        case 'pon':
        case 'kan':
        case 'addkan':
            handleFuro(message);
            break
        case 'riichi':
            handleRiichi(message);
            break
        case 'agari':
            handleAgari(message);
            break
        case 'ryuukyoku':
            handleRyuukyoku(message);
            break
        case 'settlement':
            handleSettlement(message);
            break
        case 'select_tile':
            handleSelectTile(message);
            break
        case 'decision':
            handleDecision(message);
            break
        case 'score':
            handleScore(message);
            break
        case 'end':
            alert('游戏结束！请重新连接～');
            ws.close();
            document.getElementById("connecting-form").style.display = 'block';
            break
    }
}
