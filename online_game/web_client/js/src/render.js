let windowWidth = window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;
let windowHeight = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;

// 保证游戏界面始终是正方形
let defaultDimension = 889;
let minDimension = Math.min(windowWidth, windowHeight);
let globalScaleRate = minDimension / defaultDimension;
let scene;
let displayWidth0 = 72;
let displayHeight0 = 109;
let displayWidth1 = 89;
let displayHeight1 = 97;
let tileWidth0 = 72;
let tileHeight0 = 80;
let tileWidth1 = 60;
let tileHeight1 = 97;

window.addEventListener('resize', () => {
    // minDimension = Math.min(windowWidth, windowHeight);
    // globalScaleRate = minDimension / defaultDimension;
})

function mod(n, m){
    return ((n % m) + m) % m;
}

function argMax(array) {
  return [].reduce.call(array, (m, c, i, arr) => c > arr[m] ? i : m, 0)
}

function splitArray(arr) {
  const len = arr.length;
  if (len > 16 || len < 1) {
    return "Invalid array length";
  }

  const maxSubArrayLen = 4;
  const maxSubArrays = 4;

  let remaining = len;
  let numSubArrays = Math.min(Math.ceil(len / maxSubArrayLen), maxSubArrays);
  let result = [];

  while (remaining > 0) {
    let currentSubArrayLen = Math.ceil(remaining / numSubArrays);
    result.push(arr.slice(len - remaining, len - remaining + currentSubArrayLen));
    remaining -= currentSubArrayLen;
    numSubArrays--;
  }

  return result;
}

class BlockingQueue {
  constructor() {
    this.queue = [];
    this.resolvers = [];
  }

  enqueue(item) {
    const resolver = this.resolvers.shift();
    if (resolver) {
      resolver(item);
    } else {
      this.queue.push(item);
    }
  }

  async dequeue() {
    if (this.queue.length > 0) {
      return this.queue.shift();
    } else {
      return new Promise(resolve => {
        this.resolvers.push(resolve);
      });
    }
  }
}

class MahjongScene extends Phaser.Scene {
    #handTiles=null
    #rightHand=null
    #oppoHand=null
    #leftHand=null
    #gameInfo=null
    #playerInfo=null
    #leftTileCount=null
    #riichiBa=null
    #yellowBars=null
    #dora=null
    #river=null
    #furitenMark=null
    #furo=null
    #wsFcn=null
    #settlement=null
    #drawSound=null
    #discardSound=null
    #chiSound=null
    #ponSound=null
    #kanSound=null
    #riichiSound=null
    #wRiichiSound=null
    #ronSound=null
    #tsumoSound=null
    #decisionSound=null
    #settlementSound=null
    constructor() {
        super({ key: 'MahjongScene' });
        this.selectTile = false;
        this.queue = new BlockingQueue();
    }

    preload () {
        alert("正在加载静态资源...");
        this.load.on('complete', function (loader, totalComplete, totalFailed) {
            if (totalFailed === 0) {
                alert("静态资源加载完毕");
                document.getElementById("connecting-form").style.display = 'block';
            } else {
                alert("共有 " + totalFailed + " 个资源加载失败！请刷新网页重试～");
            }
        });
        this.load.image('background', 'img/background2d.png');
        this.load.spritesheet('tiles0', 'img/vieww000072.png', {frameWidth: 72, frameHeight: 109});
        this.load.spritesheet('tiles1', 'img/vieww100097.png', {frameWidth: 97, frameHeight: 89});
        this.load.spritesheet('tiles2', 'img/vieww200072.png', {frameWidth: 72, frameHeight: 109});
        this.load.spritesheet('tiles3', 'img/vieww300097.png', {frameWidth: 97, frameHeight: 89});
        this.load.spritesheet('tiles4', 'img/vieww400117.png', {frameWidth: 117, frameHeight: 177});
        this.load.image('right_tile', 'img/vieww548057.png');
        this.load.image('left_tile', 'img/vieww748057.png');

        this.load.audio('draw_sound', 'audio/draw.wav');
        this.load.audio('discard_sound', 'audio/discard.wav');
        this.load.audio('decision_sound', 'audio/decision.wav');
        this.load.audio('settlement_sound', 'audio/settlement.wav');

        this.load.audio('chi_sound0', 'audio/act_chi_29.mp3');
        this.load.audio('pon_sound0', 'audio/act_pon_29.mp3');
        this.load.audio('kan_sound0', 'audio/act_kan_29.mp3');
        this.load.audio('ron_sound0', 'audio/act_ron_35.mp3');
        this.load.audio('riichi_sound0', 'audio/act_rich_42.mp3');
        this.load.audio('w_riichi_sound0', 'audio/act_drich_17.mp3')
        this.load.audio('tsumo_sound0', 'audio/act_tumo_9.mp3');

        this.load.audio('chi_sound1', 'audio/chi.wav');
        this.load.audio('pon_sound1', 'audio/pon.wav');
        this.load.audio('kan_sound1', 'audio/kan.wav');
        this.load.audio('ron_sound1', 'audio/ron.wav');
        this.load.audio('riichi_sound1', 'audio/riichi.wav');
        this.load.audio('w_riichi_sound1', 'audio/riichi.wav')
        this.load.audio('tsumo_sound1', 'audio/tsumo.wav');
    }

    setWsFcn(fcn){
        this.#wsFcn = fcn;
    }

    getTileFrameIndex(tileId) {
        let akas = [16, 52, 88];
        let tile = Math.floor(tileId / 4);

        let row, col, frameIndex;
        if (akas.includes(tileId)){
            row = akas.indexOf(tileId);
            col = 0;
        } else {
            row = Math.floor(tile / 9);
            col = tile % 9 + 1;
        }

        frameIndex = row * 10 + col;
        return frameIndex;
    }

    setHandTileInteractivity(tile) {
        tile.setInteractive();
        tile.on('pointerover', () => {
            tile.y = this.sys.canvas.height - 75 * globalScaleRate;
        });

        tile.on('pointerout', () => {
            tile.y = this.sys.canvas.height - 60 * globalScaleRate;
        });
        tile.on('pointerdown', () => {
            if (this.selectTile) {
                this.selectTile = false;
                const index = this.#handTiles.getChildren().indexOf(tile);
                this.queue.enqueue(index);
            }
        })
    }

    renderDraw(seat, who, tileId) {
        if (document.hasFocus()) this.#drawSound.play();
        let relativePos = mod(who - seat, 4);
        let imageSet;
        let startX = this.sys.canvas.width / 2;
        let startY = this.sys.canvas.height / 2;
        let scale;
        let targetX, targetY;
        let frameIndex;
        let tile;
        let length;
        switch (relativePos) {
            case 0:
                length = this.#handTiles.getChildren().length;
                scale = globalScaleRate * 0.45;
                targetX = 40 * globalScaleRate + (117 + 2) * scale * (length + 1) + 10 * scale;
                targetY = this.sys.canvas.height - 60 * globalScaleRate;
                imageSet = 'tiles4';
                frameIndex = this.getTileFrameIndex(tileId);
                tile = this.#handTiles.create(startX, startY, imageSet, frameIndex).setAlpha(0).setDepth(1000).setScale(scale);
                this.setHandTileInteractivity(tile);
                break
            case 1:
                length = this.#rightHand.getChildren().length;
                scale = globalScaleRate * 0.5;
                let bottom = this.sys.canvas.height - 450 * scale;
                targetX = this.sys.canvas.width - 57 * scale;
                targetY = bottom - (132 * scale - 61 * scale) * (length) - 30 * scale;
                imageSet = 'right_tile';
                tile = this.#rightHand.create(startX, startY, imageSet).setAlpha(0).setDepth(0).setScale(scale);
                break
            case 2:
                length = this.#oppoHand.getChildren().length;
                scale = globalScaleRate * 0.5;

                targetX = this.sys.canvas.width - 350 * scale - displayWidth0 * scale * (length + 1) - 20 * scale;
                targetY = 50 * scale;
                imageSet = 'tiles2';
                tile = this.#oppoHand.create(startX, startY, imageSet, 30).setAlpha(0).setDepth(10).setScale(scale);
                break
            case 3:
                length = this.#leftHand.getChildren().length;
                scale = globalScaleRate * 0.5;
                targetX = 57 * scale;
                targetY = 350 * scale + (132 * scale - 60 * scale) * (length) + 20 * scale;
                imageSet = 'left_tile';
                tile = this.#leftHand.create(startX, startY, imageSet).setAlpha(0).setDepth(length).setScale(scale);
                break
        }
        this.tweens.add({
            targets: tile,
            x: targetX,
            y: targetY,
            alpha: 1,
            duration: 200,
            ease: 'Power2'
        });
    }

    renderDiscard(seat, who, discardTile, discardIndex, riichi) {
        if (document.hasFocus()) this.#discardSound.play();
        let relativePos = mod(who - seat, 4);
        let x, y, tiles, length;
        switch (relativePos) {
            case 0:
                tiles = this.#handTiles.getChildren();
                break
            case 1:
                tiles = this.#rightHand.getChildren();
                break
            case 2:
                tiles = this.#oppoHand.getChildren();
                break
            case 3:
                tiles = this.#leftHand.getChildren();
                break
        }
        length = tiles.length;
        if (discardIndex === null) {
            discardIndex = Math.floor(Math.random() * (length - 1));
        } else if (discardIndex === -1) {
            discardIndex = length - 1;
        }
        let tile = tiles[discardIndex];
        x = tile.x;
        y = tile.y;
        tile.destroy();
        this.addRiver(seat, who, discardTile, x, y, riichi)
    }

    renderHand(hand) {
        this.#handTiles.clear(true, true);
        let x = 40 * globalScaleRate;
        let y = this.sys.canvas.height - 60 * globalScaleRate;
        let scale = globalScaleRate * 0.45;

        for (let i = 0; i < hand.length; i++) {

            x += (117 + 2) * scale;
            let code = hand[i];
            let frameIndex = this.getTileFrameIndex(code);

            let tile = this.#handTiles.create(x, y, 'tiles4', frameIndex).setScale(scale).setDepth(1000);
            this.setHandTileInteractivity(tile);
        }
    }

    renderRightHand(length) {
        this.#rightHand.clear(true, true);


        let scale = globalScaleRate * 0.5;

        let bottom = this.sys.canvas.height - 450 * scale;
        let imageWidth = 57 * scale;
        let imageHeight = 132 * scale;

        let x = this.sys.canvas.width - imageWidth;
        let y = bottom - (imageHeight - 60 * scale) * length;


        for (let i = 0; i < length; i++) {
            y += (imageHeight - 60 * scale);
            let image = this.add.image(x, y, 'right_tile').setScale(scale).setDepth(i + 1);
            this.#rightHand.add(image);
        }
    }

    renderOppoHand(length) {
        this.#oppoHand.clear(true, true);

        let scale = globalScaleRate * 0.5;

        let imageWidth = 72 * scale;

        let x = this.sys.canvas.width - 350 * scale;
        let y = 50 * scale;

        for (let i = 0; i < length; i++) {
            x -= imageWidth;
            this.#oppoHand.create(x, y, 'tiles2', 30).setScale(scale).setDepth(10);
        }
    }

    renderLeftHand(length) {
        this.#leftHand.clear(true, true);

        let scale = globalScaleRate * 0.5;

        let imageWidth = 57 * scale;
        let imageHeight = 132 * scale;

        let x = imageWidth;
        let y = 350 * scale;


        for (let i = 0; i < length; i++) {
            let image = this.add.image(x, y, 'left_tile').setScale(scale).setDepth(i + 1);
            this.#leftHand.add(image);
            y += (imageHeight - 60 * scale);
        }
    }

    renderHonba(honba) {
        let centerX = this.sys.canvas.width / 2;
        let centerY = this.sys.canvas.height / 2;
        let graphics = this.add.graphics();
        graphics.fillStyle(0xFFFFFF, 1);
        let rectX = centerX - 10 * globalScaleRate;
        let rectY = centerY + 30 * globalScaleRate;
        let rectWidth = 10 * globalScaleRate;
        let rectHeight = 20 * globalScaleRate;
        this.#gameInfo.add(graphics.fillRect(rectX, rectY, rectWidth, rectHeight));
        graphics.fillStyle(0x000000, 1);
        let dotRadius = globalScaleRate;
        let rows = 3;
        let cols = 2;

        for (let i = 0; i < rows; i++) {
            for (let j = 0; j < cols; j++) {
                let dotX = rectX + rectWidth / 3 * (j + 1);
                let dotY = rectY + rectHeight / 4 * (i + 1);
                this.#gameInfo.add(graphics.fillCircle(dotX, dotY, dotRadius));
            }
        }
        let style = {
            fontFamily: 'Arial',
            fontSize: 20 * globalScaleRate + 'px',
            color: '#ffffff'
        }
        let offsetX = - 20 * globalScaleRate / 2;
        let offsetY = 80 * globalScaleRate / 2;
        this.#gameInfo.add(this.add.text(centerX - offsetX, centerY + offsetY, honba, style).setOrigin(0.5));
    }

    renderGameInfo(gameRound, honba) {
        this.#gameInfo.clear(true, true);
        this.#yellowBars.clear(true, true);
        let graphics = this.add.graphics();
        let sideLength = 250;
        graphics.lineStyle(5 * globalScaleRate, 0xFFFFFF, 1);
        graphics.fillStyle(0x333333, 1);
        let centerX = this.sys.canvas.width / 2;
        let centerY = this.sys.canvas.height / 2;
        let x = centerX - sideLength * globalScaleRate / 2;
        let y = centerY - sideLength * globalScaleRate / 2;
        this.#gameInfo.add(graphics.strokeRoundedRect(x, y, sideLength * globalScaleRate, 250 * globalScaleRate, 15 * globalScaleRate));
        this.#gameInfo.add(graphics.fillRoundedRect(x, y, sideLength * globalScaleRate, 250 * globalScaleRate, 15 * globalScaleRate));
        let style = {
            fontFamily: 'Verdana',
            fontSize: 36 * globalScaleRate + 'px',
            fontStyle: 'bold',
            color: '#FFFFFF',  // 内部颜色
            stroke: '#FF0000',  // 边缘颜色
            strokeThickness: 3 * globalScaleRate,
            shadow: {
                offsetX: 1,
                offsetY: 1,
                color: '#000',
                blur: 10 * globalScaleRate,
                stroke: true,
                fill: true
            }
        };
        let wind = ['東', '南', '西', '北'][Math.floor(gameRound / 4)]
        let wind_round = gameRound % 4 + 1
        this.#gameInfo.add(this.add.text(centerX, centerY, wind + wind_round + '局', style).setOrigin(0.5));

        this.renderHonba(honba);

        let barLength = 220 * globalScaleRate;
        let barWidth = 8 * globalScaleRate;

        // 绘制底部黄色条
        let bar0 = this.add.rectangle(centerX, centerY + (sideLength - 5) * globalScaleRate / 2, barLength, barWidth, 0xFFFF00).setAlpha(0);

        // 绘制右侧黄色条
        let bar1 = this.add.rectangle(centerX + (250 - 5) * globalScaleRate / 2, centerY, barWidth, barLength, 0xFFFF00).setAlpha(0);

        // 绘制顶部黄色条
        let bar2 = this.add.rectangle(centerX, centerY - (sideLength - 5) * globalScaleRate / 2, barLength, barWidth, 0xFFFF00).setAlpha(0);

        // 绘制左侧黄色条
        let bar3 = this.add.rectangle(centerX - (sideLength - 5) * globalScaleRate / 2, centerY, barWidth, barLength, 0xFFFF00).setAlpha(0);
        this.#yellowBars.addMultiple([bar0, bar1, bar2, bar3]);
    }

    toggleBlink(who) {
        this.#yellowBars.getChildren().forEach((child, index) => {
            if (index === who) {
                this.tweens.add({
                    targets: child,
                    alpha: { from: 0, to: 0.5 },
                    duration: 500,
                    yoyo: true,
                    repeat: -1
                });
            } else {
                this.tweens.killTweensOf(child);
                child.setAlpha(0);
            }
        });
    }

    renderRiichiBa(riichiBa) {
        this.#riichiBa.clear(true, true);
        let centerX = this.sys.canvas.width / 2;
        let centerY = this.sys.canvas.height / 2;

        let graphics = this.add.graphics();
        graphics.fillStyle(0xFFFFFF, 1);
        let rectX = centerX + 25 * globalScaleRate;
        let rectY = centerY + 30 * globalScaleRate;
        let rectWidth = 10 * globalScaleRate;
        let rectHeight = 20 * globalScaleRate;
        this.#riichiBa.add(graphics.fillRect(rectX, rectY, rectWidth, rectHeight));
        graphics.fillStyle(0xff0000, 1);
        let dotRadius = 2 * globalScaleRate;
        this.#riichiBa.add(graphics.fillCircle(rectX + rectWidth / 2, rectY + rectHeight / 2, dotRadius));

        let style = {
            fontFamily: 'Arial',
            fontSize: 20 * globalScaleRate + 'px',
            color: '#ffffff'
        }
        let offsetX = - 90 * globalScaleRate / 2;
        let offsetY = 80 * globalScaleRate / 2;
        this.#riichiBa.add(this.add.text(centerX - offsetX, centerY + offsetY, riichiBa, style).setOrigin(0.5));
    }

    renderPlayerInfo(selfSeat, who, username, score, oya, observer=false) {
        this.#playerInfo[who].clear(true, true);
        let width = this.sys.canvas.width;
        let height = this.sys.canvas.height;
        let centerX = width / 2;
        let centerY = height / 2;
        let sideLength = 250;
        let windOffset = (sideLength - 40) * globalScaleRate / 2;
        let relativePos = mod(who - selfSeat, 4);
        let wind = mod(who - oya, 4);
        let windStyle;
        if (wind === 0) {
            windStyle = {
                fontFamily: 'Kai',
                fontSize: 30 * globalScaleRate + 'px',
                color: '#ffffff'
            };
        } else {
            windStyle = {
                fontFamily: 'Kai',
                fontSize: 24 * globalScaleRate + 'px',
                color: '#888888'
            };
        }
        wind = ['東', '南', '西', '北'][wind];
        let scoreStyle = {
            fontFamily: 'Arial',
            fontSize: 30 * globalScaleRate + 'px',
            color: '#ffffff'
        }
        let usernameStyle = {
            fontFamily: 'Kai',
            fontSize: 24 * globalScaleRate + 'px',
            color: '#ffffff',
            wordWrap: {
                width: 150 * globalScaleRate,
                useAdvancedWrap: true
            },
            align: 'center'
        }
        let usernameRect, usernameText;
        let usernameOffset = 240 * globalScaleRate;
        switch (relativePos) {
            case 0:
                wind = this.add.text(centerX - 100 * globalScaleRate, centerY + windOffset, wind, windStyle).setOrigin(0.5).setAngle(0);
                score = this.add.text(centerX, centerY + windOffset, score, scoreStyle).setOrigin(0.5).setAngle(0);
                usernameRect = this.add.rectangle(usernameOffset, height - usernameOffset, 150 * globalScaleRate, 150 * globalScaleRate, 0x222222).setAlpha(0.2);
                usernameText = this.add.text(usernameOffset, height - usernameOffset, username, usernameStyle).setOrigin(0.5).setAngle(0).setAlpha(0.3);
                break
            case 1:
                wind = this.add.text(centerX + windOffset, centerY + 100 * globalScaleRate, wind, windStyle).setOrigin(0.5).setAngle(-90);
                score = this.add.text(centerX + windOffset, centerY, score, scoreStyle).setOrigin(0.5).setAngle(-90);
                usernameRect = this.add.rectangle(width - usernameOffset, height - usernameOffset, 150 * globalScaleRate, 150 * globalScaleRate, 0x222222).setAlpha(0.2);
                usernameText = this.add.text(width - usernameOffset, height - usernameOffset, username, usernameStyle).setOrigin(0.5).setAngle(-90).setAlpha(0.3);
                break
            case 2:
                wind = this.add.text(centerX + 100 * globalScaleRate, centerY - windOffset, wind, windStyle).setOrigin(0.5).setAngle(180);
                score = this.add.text(centerX, centerY - windOffset, score, scoreStyle).setOrigin(0.5).setAngle(180);
                usernameRect = this.add.rectangle(width - usernameOffset, usernameOffset, 150 * globalScaleRate, 150 * globalScaleRate, 0x222222).setAlpha(0.2);
                usernameText = this.add.text(width - usernameOffset, usernameOffset, username, usernameStyle).setOrigin(0.5).setAngle(180).setAlpha(0.3);
                break
            case 3:
                wind = this.add.text(centerX - windOffset, centerY - 100 * globalScaleRate, wind, windStyle).setOrigin(0.5).setAngle(90);
                score = this.add.text(centerX - windOffset, centerY, score, scoreStyle).setOrigin(0.5).setAngle(90);
                usernameRect = this.add.rectangle(usernameOffset, usernameOffset, 150 * globalScaleRate, 150 * globalScaleRate, 0x222222).setAlpha(0.2);
                usernameText = this.add.text(usernameOffset, usernameOffset, username, usernameStyle).setOrigin(0.5).setAngle(90).setAlpha(0.3);
                break
        }
        if (observer) {
            usernameRect.setInteractive();
            usernameRect.on('pointerover', () => {
                this.input.setDefaultCursor('pointer');
            });
            usernameRect.on('pointerout', () => {
                this.input.setDefaultCursor('default');
            });
            usernameRect.on('pointerdown', () => {
                this.#wsFcn({'event': 'change_ob', 'username': username});
                this.input.setDefaultCursor('default');
            });
        }
        this.#playerInfo[who].addMultiple([wind, score, usernameRect, usernameText]);
    }

    renderLeftTileCount(leftTile) {
        this.#leftTileCount.clear(true, true);
        let centerX = this.sys.canvas.width / 2;
        let centerY = this.sys.canvas.height / 2;
        let offsetX = 60 * globalScaleRate / 2;
        let offsetY = 80 * globalScaleRate / 2;

        let style = {
            fontFamily: 'Arial',
            fontSize: 20 * globalScaleRate + 'px',
            color: '#ffffff'
        }
        this.#leftTileCount.add(this.add.text(centerX - offsetX, centerY + offsetY, leftTile, style).setOrigin(0.5));
    }

    renderDora(doraIndicator) {
        this.#dora.clear(true, true);
        let centerX = this.sys.canvas.width / 2;
        let centerY = this.sys.canvas.height / 2;
        let offsetX = 170 * globalScaleRate / 2;
        let offsetY = 120 * globalScaleRate / 2;
        let scale = globalScaleRate * 0.4;
        let x = centerX - offsetX;
        let y = centerY - offsetY;

        doraIndicator = doraIndicator.map(this.getTileFrameIndex).concat(Array(5 - doraIndicator.length).fill(30));
        doraIndicator.forEach((item) => {
            x += 70 * scale;
            this.#dora.create(x, y + 15 * globalScaleRate, 'tiles0', 30).setScale(scale);
            this.#dora.create(x, y, 'tiles0', item).setScale(scale);
        });
    }

    renderRiver(seat, who, river, riichiTile) {
        this.#river[who].clear(true, true);
        let centerX = this.sys.canvas.width / 2;
        let centerY = this.sys.canvas.height / 2;
        let sideLength = 250;
        let scale;
        let relativePos = mod(who - seat, 4);
        let startX, startY;
        let tileImgSet, riichiImgSet;
        let x, y;
        switch (relativePos) {
            case 0:
                scale = 0.52 * globalScaleRate;
                tileImgSet = 'tiles0';
                riichiImgSet = 'tiles1';
                startX = centerX - sideLength * globalScaleRate / 2 + 10 * globalScaleRate;
                startY = centerY + sideLength * globalScaleRate / 2 + 3 * globalScaleRate;
                x = startX;
                y = startY;
                for (let i = 0; i < river.length; i++) {
                    if (i > 0 && i % 6 === 0) {
                        x = startX;
                        y += tileHeight0 * scale
                    }
                    let code = river[i];
                    let frameIndex = this.getTileFrameIndex(code);

                    if (code === riichiTile) {
                        this.#river[who].create(x, y + (tileHeight0 - tileWidth1) * scale, riichiImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayHeight1 * scale, displayWidth1 * scale).setDepth(1 + Math.floor(i / 6));
                        x += tileHeight1 * scale;
                    } else {
                        this.#river[who].create(x, y, tileImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayWidth0 * scale, displayHeight0 * scale).setDepth(1 + Math.floor(i / 6));
                        x += tileWidth0 * scale;
                    }
                }
                break
            case 1:
                scale = 0.5 * globalScaleRate;
                tileImgSet = 'tiles1';
                riichiImgSet = 'tiles2';
                startX = centerX + sideLength * globalScaleRate / 2 + 3 * globalScaleRate;
                startY = centerY + sideLength * globalScaleRate / 2 - 60 * globalScaleRate;
                x = startX;
                y = startY;
                for (let i = 0; i < river.length; i++) {
                    if (i > 0 && i % 6 === 0) {
                        y = startY;
                        x += tileHeight1 * scale;
                    }
                    let code = river[i];
                    let frameIndex = this.getTileFrameIndex(code);

                    if (code === riichiTile) {
                        y -= (tileHeight0 - tileWidth1) * scale;
                        this.#river[who].create(x + (tileHeight1 - tileWidth0) * scale, y, riichiImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayWidth0 * scale, (displayHeight0 + 5) * scale).setDepth(6 - i % 6);
                        y -= tileWidth1  * scale;
                    } else {
                        this.#river[who].create(x, y, tileImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayHeight1 * scale, (displayWidth1 + 5) * scale).setDepth(6 - i % 6);
                        y -= (tileWidth1 + 5) * scale;
                    }
                }
                break
            case 2:
                scale = 0.52 * globalScaleRate;
                tileImgSet = 'tiles2';
                riichiImgSet = 'tiles3';
                startX = centerX + sideLength * globalScaleRate / 2 - 45 * globalScaleRate;
                startY = centerY - sideLength * globalScaleRate / 2 - 60 * globalScaleRate;
                x = startX;
                y = startY;
                for (let i = 0; i < river.length; i++) {
                    if (i > 0 && i % 6 === 0) {
                        x = startX;
                        y -= tileHeight0 * scale;
                    }
                    let code = river[i];
                    let frameIndex = this.getTileFrameIndex(code);

                    if (code === riichiTile) {
                        x -= (tileHeight1 - tileWidth0) * scale;
                        this.#river[who].create(x, y, riichiImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayHeight1 * scale, displayWidth1 * scale).setDepth(5 - Math.floor(i / 6));
                        x -= tileWidth0 * scale;
                    } else {
                        this.#river[who].create(x, y, tileImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayWidth0 * scale, displayHeight0 * scale).setDepth(5 - Math.floor(i / 6));
                        x -= tileWidth0 * scale;
                    }
                }
                break
            case 3:
                scale = 0.5 * globalScaleRate;
                tileImgSet = 'tiles3';
                riichiImgSet = 'tiles0';
                startX = centerX - sideLength * globalScaleRate / 2 - 53 * globalScaleRate;
                startY = centerY - sideLength * globalScaleRate / 2 + 10 * globalScaleRate;
                x = startX;
                y = startY;
                for (let i = 0; i < river.length; i++) {
                    if (i > 0 && i % 6 === 0) {
                        y = startY;
                        x -= tileHeight1 * scale;
                    }
                    let code = river[i];
                    let frameIndex = this.getTileFrameIndex(code);

                    if (code === riichiTile) {
                        this.#river[who].create(x, y, riichiImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayWidth0 * scale, (displayHeight0 + 5) * scale).setDepth(1 + i % 6);
                        y += (tileHeight0 + 5) * scale;
                    } else {
                        this.#river[who].create(x, y, tileImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayHeight1 * scale, (displayWidth1 + 5) * scale).setDepth(1 + i % 6);
                        y += (tileWidth1 + 5) * scale;
                    }
                }
                break
        }

    }

    addRiver(seat, who, code, discardX, discardY, riichi=false) {
        let river = this.#river[who];
        let centerX = this.sys.canvas.width / 2;
        let centerY = this.sys.canvas.height / 2;
        let sideLength = 250;
        let relativePos = mod(who - seat, 4);
        let startX, startY;
        let tileImgSet, riichiImgSet;
        let scale = 0.7 * globalScaleRate;
        let x, y;
        let children = river.getChildren();
        let length = children.length;
        let renderRow = Math.floor(length / 6);
        let renderCol = (length + 1) % 6;
        let tileSprite;
        let frameIndex = this.getTileFrameIndex(code);
        switch (relativePos) {
            case 0:
                scale = 0.52 * globalScaleRate;
                tileImgSet = 'tiles0';
                riichiImgSet = 'tiles1';
                startX = centerX - sideLength * globalScaleRate / 2 + 10 * globalScaleRate;
                startY = centerY + sideLength * globalScaleRate / 2 + 3 * globalScaleRate;
                y = startY + tileHeight0 * scale * renderRow;
                if (renderCol === 1) {
                    x = startX;
                } else {
                    x = children[length - 1].x;
                    let w = children[length - 1].displayWidth;
                    if (w / scale > 80) {
                        x += scale * displayHeight1;
                    } else {
                        x += scale * displayWidth0;
                    }
                }
                if (riichi) {
                    tileSprite = this.add.sprite(discardX, discardY, riichiImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayHeight1 * scale, displayWidth1 * scale).setAlpha(0).setDepth(1 + Math.floor(length / 6));
                    y = y + (tileHeight0 - tileWidth1) * scale;
                } else {
                    tileSprite = this.add.sprite(discardX, discardY, tileImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayWidth0 * scale, displayHeight0 * scale).setAlpha(0).setDepth(1 + Math.floor(length / 6));
                }
                break
            case 1:
                scale = 0.5 * globalScaleRate;
                tileImgSet = 'tiles1';
                riichiImgSet = 'tiles2';
                startX = centerX + sideLength * globalScaleRate / 2 + 3 * globalScaleRate;
                startY = centerY + sideLength * globalScaleRate / 2 - 60 * globalScaleRate;
                x = startX + displayHeight1 * scale * renderRow;
                if (renderCol === 1) {
                    y = startY;
                } else {
                    y = children[length - 1].y - (tileWidth1 + 5) * scale;
                }
                if (riichi) {
                    y -= (tileHeight0 - tileWidth1) * scale;
                    x += (tileHeight1 - tileWidth0) * scale;
                    tileSprite = this.add.sprite(discardX, discardY, riichiImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayWidth0 * scale, (displayHeight0 + 5) * scale).setDepth(6 - length % 6).setAlpha(0);
                } else {
                    tileSprite = this.add.sprite(discardX, discardY, tileImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayHeight1 * scale, (displayWidth1 + 5) * scale).setDepth(6 - length % 6).setAlpha(0);
                }
                break
            case 2:
                scale = 0.52 * globalScaleRate;
                tileImgSet = 'tiles2';
                riichiImgSet = 'tiles3';
                startX = centerX + sideLength * globalScaleRate / 2 - 45 * globalScaleRate;
                startY = centerY - sideLength * globalScaleRate / 2 - 60 * globalScaleRate;
                y = startY - tileHeight0 * scale * renderRow;
                if (renderCol === 1) {
                    x = startX;
                } else {
                    x = children[length - 1].x - tileWidth0 * scale;
                }
                if (riichi) {
                    x -= (tileHeight1 - tileWidth0) * scale;
                    tileSprite = this.add.sprite(discardX, discardY, riichiImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayHeight1 * scale, displayWidth1 * scale).setDepth(5 - Math.floor(length / 6)).setAlpha(0);
                } else {
                    tileSprite = this.add.sprite(discardX, discardY, tileImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayWidth0 * scale, displayHeight0 * scale).setDepth(5 - Math.floor(length / 6)).setAlpha(0);
                }
                break
            case 3:
                scale = 0.5 * globalScaleRate;
                tileImgSet = 'tiles3';
                riichiImgSet = 'tiles0';
                startX = centerX - sideLength * globalScaleRate / 2 - 53 * globalScaleRate;
                startY = centerY - sideLength * globalScaleRate / 2 + 10 * globalScaleRate;
                x = startX - displayHeight1 * scale * renderRow;
                if (renderCol === 1) {
                    y = startY;
                } else {
                    let h = children[length - 1].displayHeight;
                    y = children[length - 1].y;
                    if (h / scale > 100) {
                        y += scale * (tileHeight0 + 5);
                    } else {
                        y += scale * (tileWidth1 + 5);
                    }
                }
                if (riichi) {
                    tileSprite = this.add.sprite(discardX, discardY, riichiImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayWidth0 * scale, (displayHeight0+5) * scale).setAlpha(0).setDepth(1 + length % 6);
                } else {
                    tileSprite = this.add.sprite(discardX, discardY, tileImgSet, frameIndex).setOrigin(0, 0).setDisplaySize(displayHeight1 * scale, (displayWidth1+5) * scale).setAlpha(0).setDepth(1 + length % 6);
                }
                break
        }

        river.add(tileSprite);
        this.tweens.add({
            targets: tileSprite,
            x: x,
            y: y,
            alpha: 1,
            duration: 200,
            ease: 'Power2'
        });
    }

    popFromRiver(who) {
        let river = this.#river[who];
        let children = river.getChildren();
        let lastChild = children[children.length - 1];
        let x = lastChild.x;
        let y = lastChild.y;
        if (lastChild) {
            river.remove(lastChild, true, true);
        }
        return [x, y];
    }

    renderAction(seat, who, actionText, isAI) {
        let audioIdx = isAI?0:1;
        switch (actionText) {
            case '吃':
                if (document.hasFocus()) this.#chiSound[audioIdx].play();
                break;
            case '碰':
                if (document.hasFocus()) this.#ponSound[audioIdx].play();
                break;
            case '杠':
                if (document.hasFocus()) this.#kanSound[audioIdx].play();
                break;
            case '立直':
                if (document.hasFocus()) this.#riichiSound[audioIdx].play();
                break;
            case 'w立直':
                actionText = '立直';
                if (document.hasFocus()) this.#wRiichiSound[audioIdx].play();
                break;
            case '荣':
                if (document.hasFocus()) this.#ronSound[audioIdx].play();
                break;
            case '自摸':
                if (document.hasFocus()) this.#tsumoSound[audioIdx].play();
                break;
        }
        let style = {
            fontFamily: 'Kai',
            fontSize: 100 * globalScaleRate + 'px',
            color: '#ffffff',
            stroke: 3 * globalScaleRate,
            strokeColor: '#000000',
            shadow: {
                offsetX: globalScaleRate,
                offsetY: globalScaleRate,
                color: '#000000',
                stroke: true,
                fill: true
            }
        }
        let width = this.sys.canvas.width;
        let height = this.sys.canvas.height;
        let offset = 150 * globalScaleRate;
        let x, y;
        let relativePos = mod(who - seat, 4);
        switch (relativePos) {
            case 0:
                x = width / 2;
                y = height - offset;
                break
            case 1:
                x = width - offset;
                y = height / 2;
                break
            case 2:
                x = width / 2;
                y = offset;
                break
            case 3:
                x = offset;
                y = height / 2;
                break
        }
        let text = this.add.text(x, y, actionText, style).setOrigin(0.5, 0.5).setDepth(1000);
        this.tweens.add({
            targets: text,
            scaleX: 0.7,
            scaleY: 0.7,
            alpha: 1,
            duration: 600,
            ease: 'Power2',
            onComplete: function () {
                text.destroy();
            }
        });
    }

    renderOthersOpenHand(seat, who, hai, tsumo) {
        let relativePos = mod(who - seat, 4);
        let frameIndexList;
        let display;
        if (Array.isArray(hai)){
            frameIndexList = hai.map(this.getTileFrameIndex);
            display = true;
        } else {
            frameIndexList = new Array(hai).fill(30);
            display = false;
        }
        let length = frameIndexList.length;
        let startX, startY, deltaX, deltaY;
        let tileImageSet;
        let scale;
        let area;
        switch (relativePos) {
            case 1:
                area = this.#rightHand;
                area.clear(true, true);
                frameIndexList.reverse();
                scale = 0.6 * globalScaleRate;
                tileImageSet = 'tiles1';

                let bottom = this.sys.canvas.height - 300  * scale;

                startX = this.sys.canvas.width - displayHeight1 * scale * 0.6;
                startY = bottom - tileWidth1 * scale * length;
                deltaX = 0;
                deltaY = 60 * scale;
                if (tsumo) startY -= 20 * scale;
                break
            case 2:
                area = this.#oppoHand;
                area.clear(true, true);
                scale = 0.55 * globalScaleRate;
                if (display){
                    tileImageSet = 'tiles2';
                } else {
                    tileImageSet = 'tiles0';
                }
                startX = this.sys.canvas.width - 380 * scale;
                startY = 60 * scale;
                deltaX = - 72 * scale
                deltaY = 0;
                break
            case 3:
                area = this.#leftHand;
                area.clear(true, true);
                scale = 0.55 * globalScaleRate;
                if (display){
                    tileImageSet = 'tiles3';
                } else {
                    tileImageSet = 'tiles1';
                }
                let top = 350  * scale;

                startX = displayHeight1 * scale * 0.65;
                startY = top;
                deltaX = 0;
                deltaY = 60 * scale;
                break
        }
        let x = startX, y = startY;
        for (let i = 0; i < length; i++){
            let frameIndex = frameIndexList[i];
            area.create(x, y, tileImageSet, frameIndex).setScale(scale);
            x += deltaX;
            y += deltaY;
            if (tsumo) {
                switch (relativePos) {
                    case 1:
                        if (i === 0) y += 20 * scale;
                        break
                    case 2:
                        if (i === length - 2) x -= 24 * scale;
                        break
                    case 3:
                        if (i === length - 2) y += 20 * scale;
                        break
                }
            }
        }
    }

    renderFuriten(furiten) {
        if (!furiten && this.#furitenMark !== null) {
            this.#furitenMark.destroy();
            this.#furitenMark = null;
        } else if (furiten && this.#furitenMark === null) {
            let style = {
                fontFamily: 'Kai',
                fontSize: 20 * globalScaleRate + 'px',
                color: '#ffff00'
            }
            let x = 95 * globalScaleRate;
            let y = this.sys.canvas.height - 120 * globalScaleRate;
            this.#furitenMark = this.add.text(x, y, '振听', style).setOrigin(0.5, 0.5).setDepth(1000);
        }
    }

    parseFuro(who, tileList, kuiInfo) {
        tileList.sort((a, b) => a - b);
        let extra = null, kuiTile, kuiPos, fromWho, frameIndexList;
        if (kuiInfo.length === 3) { //加杠
            [extra, kuiTile, fromWho] = kuiInfo;
            kuiPos = 3 - mod(fromWho - who, 4);
            frameIndexList = tileList.filter(item => item !== extra && item !== kuiTile).map(this.getTileFrameIndex);
            frameIndexList.splice(kuiPos, 0, this.getTileFrameIndex(kuiTile));
            extra = this.getTileFrameIndex(extra);
        }
        else {
            [kuiTile, fromWho] = kuiInfo;
            if (fromWho === who) { //暗杠
                kuiTile = Math.min(...tileList);
                kuiPos = 1;
                extra = kuiTile + 1;
                frameIndexList = [30, this.getTileFrameIndex(kuiTile), 30];
                extra = this.getTileFrameIndex(extra);
            } else {
                kuiPos = 3 - mod(fromWho - who, 4);
                frameIndexList = tileList.filter(item => item !== kuiTile).map(this.getTileFrameIndex);
                if (tileList.length === 4) {
                    [extra, ...frameIndexList] = frameIndexList;
                }
                frameIndexList.splice(kuiPos, 0, this.getTileFrameIndex(kuiTile));
            }
        }
        return [frameIndexList, kuiPos, extra];
    }

    renderFuros(seat, who, furoList, kuiInfoList) {
        Object.entries(this.#furo[who]).forEach(([key, value]) => {
                value.clear(true, true);
                delete this.#furo[who][key];
            });
        furoList = Object.entries(furoList);
        furoList.reverse();
        kuiInfoList.reverse();
        let width = this.sys.canvas.width, height = this.sys.canvas.height;
        let furoLength = kuiInfoList.length;
        let startX, startY, x, y;
        let scale = 0.5 * globalScaleRate;
        let imageSet0, imageSet1, imageSet2;
        let relativePos = mod(who - seat, 4);
        let furoWidth;
        let group;
        let frameIndexList, kuiPos, extra;
        switch (relativePos) {
            case 0:
                imageSet0 = 'tiles0';
                imageSet1 = 'tiles1';
                furoWidth = (2 * displayWidth0 + displayHeight1) * scale;
                startX = width - 50 * globalScaleRate - furoLength * furoWidth;
                startY = height - 75 * globalScaleRate;
                furoList.forEach(([key, value], index) => {
                    x = startX + index * furoWidth;
                    y = startY;
                    group = this.add.group();
                    key = key.match(/\d+/g).map(Number);
                    this.#furo[who][key] = group;
                    [frameIndexList, kuiPos, extra] = this.parseFuro(who, value, kuiInfoList[index]);
                    frameIndexList.forEach((item, index) => {
                        if (index === kuiPos) {
                            if (extra !== null) {
                                group.create(x, y + (displayHeight0 - displayWidth1 - tileWidth1) * scale, imageSet1, extra).setOrigin(0, 0).setScale(scale);
                            }
                            group.create(x, y + (displayHeight0 - displayWidth1) * scale, imageSet1, item).setOrigin(0, 0).setScale(scale);
                            x += displayHeight1 * scale;
                        } else {
                            group.create(x, y, imageSet0, item).setOrigin(0, 0).setScale(scale);
                            x += displayWidth0 * scale;
                        }
                    })
                });
                break
            case 1:
                imageSet0 = 'tiles1';
                imageSet1 = 'tiles2';
                furoWidth = (2 * tileWidth1 + tileHeight0) * scale;
                startX = width - 75 * globalScaleRate;
                startY = 50 * globalScaleRate + furoLength * furoWidth + tileHeight0 * scale;
                furoList.forEach(([key, value], index) => {
                    x = startX;
                    y = startY - index * furoWidth;
                    group = this.add.group();
                    key = key.match(/\d+/g).map(Number);
                    this.#furo[who][key] = group;
                    [frameIndexList, kuiPos, extra] = this.parseFuro(who, value, kuiInfoList[index]);
                    frameIndexList.forEach((item, index) => {
                        if (index === kuiPos) {
                            y -= tileHeight0 * scale;
                            if (extra !== null) {
                                group.create(x + (tileHeight1 - 2 * tileWidth0) * scale, y, imageSet1, extra).setOrigin(0, 0).setScale(scale).setDepth(y);
                            }
                            group.create(x + (tileHeight1 - tileWidth0) * scale, y, imageSet1, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                        } else {
                            y -= tileWidth1 * scale;
                            group.create(x, y, imageSet0, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                        }
                    })
                });
                break
            case 2:
                imageSet0 = 'tiles2';
                imageSet1 = 'tiles3';
                imageSet2 = 'tiles0';
                furoWidth = (2 * displayWidth0 + displayHeight1) * scale;
                startX = 50 * globalScaleRate + furoLength * furoWidth - displayWidth0 * scale;
                startY = 20 * globalScaleRate;
                furoList.forEach(([key, value], index) => {
                    x = startX - index * furoWidth;
                    y = startY;
                    group = this.add.group();
                    key = key.match(/\d+/g).map(Number);
                    this.#furo[who][key] = group;
                    [frameIndexList, kuiPos, extra] = this.parseFuro(who, value, kuiInfoList[index]);
                    frameIndexList.forEach((item, index) => {
                        if (index === kuiPos) {
                            group.create(x - (displayHeight1 - displayWidth0) * scale, y, imageSet1, item).setOrigin(0, 0).setScale(scale);
                            if (extra !== null) {
                                group.create(x - (displayHeight1 - displayWidth0) * scale, y + tileWidth1 * scale, imageSet1, extra).setOrigin(0, 0).setScale(scale);
                            }
                            x -= displayHeight1 * scale;
                        } else {
                            if (item === 30) {
                                group.create(x, y, imageSet2, item).setOrigin(0, 0).setScale(scale);
                            } else {
                                group.create(x, y, imageSet0, item).setOrigin(0, 0).setScale(scale);
                            }
                            x -= displayWidth0 * scale;
                        }
                    })
                });
                break
            case 3:
                imageSet0 = 'tiles3';
                imageSet1 = 'tiles0';
                imageSet2 = 'tiles1'
                furoWidth = (2 * tileWidth1 + tileHeight0) * scale;
                startX = 75 * globalScaleRate - displayHeight1 * scale;
                startY = height - 50 * globalScaleRate - furoLength * furoWidth - 2 * displayWidth0 * scale;
                furoList.forEach(([key, value], index) => {
                    x = startX;
                    y = startY + index * furoWidth;
                    group = this.add.group();
                    key = key.match(/\d+/g).map(Number);
                    this.#furo[who][key] = group;
                    [frameIndexList, kuiPos, extra] = this.parseFuro(who, value, kuiInfoList[index]);
                    frameIndexList.forEach((item, index) => {
                        if (index === kuiPos) {
                            if (extra !== null) {
                                group.create(x + tileWidth0 * scale, y, imageSet1, extra).setOrigin(0, 0).setScale(scale).setDepth(y);
                            }
                            group.create(x, y, imageSet1, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                            y += tileHeight0 * scale;
                        } else {
                            if (item === 30) {
                                group.create(x, y, imageSet2, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                            }
                            else {
                                group.create(x, y, imageSet0, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                            }
                            y += tileWidth1 * scale;
                        }
                    })
                });
        }
    }

    addFuro(seat, who, furoType, tileIdList, kuiTile, fromWho, kuiX, kuiY){
        let furos = this.#furo[who]
        let width = this.sys.canvas.width, height = this.sys.canvas.height;
        let furoLength = Object.keys(furos).length;
        let x, y;
        let scale = 0.5 * globalScaleRate;
        let imageSet0, imageSet1, imageSet2;
        let relativePos = mod(who - seat, 4);
        let furoWidth;
        let group;
        let key, frameIndexList, kuiPos, extra;
        let kuiFinalX, kuiFinalY;

        switch (furoType) {
            case 0:
               key = [0, Math.min(...tileIdList), furoLength];
               break
            default:
                key = [furoType, Math.floor(kuiTile / 4)];
                break
        }

        switch (relativePos) {
            case 0:
                imageSet0 = 'tiles0';
                imageSet1 = 'tiles1';
                furoWidth = (2 * displayWidth0 + displayHeight1) * scale;
                x = width - 50 * globalScaleRate - (furoLength + 1) * furoWidth;
                y = height - 75 * globalScaleRate;
                group = this.add.group();
                this.#furo[who][key] = group;
                [frameIndexList, kuiPos, extra] = this.parseFuro(who, tileIdList, [kuiTile, fromWho]);
                frameIndexList.forEach((item, index) => {
                    if (index === kuiPos) {
                        if (extra !== null) {
                            group.create(x, y + (displayHeight0 - displayWidth1 - tileWidth1) * scale, imageSet1, extra).setOrigin(0, 0).setScale(scale);
                        }
                        [kuiFinalX, kuiFinalY] = [x, y + (displayHeight0 - displayWidth1) * scale];
                        if (kuiX !== undefined) {
                            kuiTile = group.create(kuiX, kuiY, imageSet1, item).setOrigin(0, 0).setScale(scale).setAlpha(0);
                        } else {
                            kuiTile = group.create(kuiFinalX, kuiFinalY, imageSet1, item).setOrigin(0, 0).setScale(scale);
                        }

                        x += displayHeight1 * scale;
                    } else {
                        group.create(x, y, imageSet0, item).setOrigin(0, 0).setScale(scale);
                        x += displayWidth0 * scale;
                    }
                })
                break
            case 1:
                imageSet0 = 'tiles1';
                imageSet1 = 'tiles2';
                furoWidth = (2 * tileWidth1 + tileHeight0) * scale;
                x = width - 75 * globalScaleRate;
                y = 50 * globalScaleRate + (furoLength + 1) * furoWidth + tileHeight0 * scale;
                group = this.add.group();
                this.#furo[who][key] = group;
                [frameIndexList, kuiPos, extra] = this.parseFuro(who, tileIdList, [kuiTile, fromWho]);
                frameIndexList.forEach((item, index) => {
                    if (index === kuiPos) {
                        y -= tileHeight0 * scale;
                        if (extra !== null) {
                            group.create(x + (tileHeight1 - 2 * tileWidth0) * scale, y, imageSet1, extra).setOrigin(0, 0).setScale(scale).setDepth(y);
                        }
                        [kuiFinalX, kuiFinalY] = [x + (tileHeight1 - tileWidth0) * scale, y];
                        if (kuiX !== undefined) {
                            kuiTile = group.create(kuiX, kuiY, imageSet1, item).setOrigin(0, 0).setScale(scale).setDepth(y).setAlpha(0);
                        } else {
                            kuiTile = group.create(kuiFinalX, kuiFinalY, imageSet1, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                        }
                    } else {
                        y -= tileWidth1 * scale;
                        group.create(x, y, imageSet0, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                    }
                })
                break
            case 2:
                imageSet0 = 'tiles2';
                imageSet1 = 'tiles3';
                imageSet2 = 'tiles0';
                furoWidth = (2 * displayWidth0 + displayHeight1) * scale;
                x = 50 * globalScaleRate + (furoLength + 1) * furoWidth - displayWidth0 * scale;
                y = 20 * globalScaleRate;
                group = this.add.group();
                this.#furo[who][key] = group;
                [frameIndexList, kuiPos, extra] = this.parseFuro(who, tileIdList, [kuiTile, fromWho]);
                frameIndexList.forEach((item, index) => {
                    if (index === kuiPos) {
                        [kuiFinalX, kuiFinalY] = [x - (displayHeight1 - displayWidth0) * scale, y];
                        if (kuiX !== undefined) {
                            kuiTile = group.create(kuiX, kuiY, imageSet1, item).setOrigin(0, 0).setScale(scale).setDepth(y).setAlpha(0);
                        } else {
                            kuiTile = group.create(kuiFinalX, kuiFinalY, imageSet1, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                        }
                        if (extra !== null) {
                            group.create(x - (displayHeight1 - displayWidth0) * scale, y + tileWidth1 * scale, imageSet1, extra).setOrigin(0, 0).setScale(scale).setDepth(y);
                        }
                        x -= displayHeight1 * scale;
                    } else {
                        if (item === 30) {
                            group.create(x, y, imageSet2, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                        } else {
                            group.create(x, y, imageSet0, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                        }
                        x -= displayWidth0 * scale;
                    }
                })
                break
            case 3:
                imageSet0 = 'tiles3';
                imageSet1 = 'tiles0';
                imageSet2 = 'tiles1'
                furoWidth = (2 * tileWidth1 + tileHeight0) * scale;
                x = 75 * globalScaleRate - displayHeight1 * scale;
                y = height - 50 * globalScaleRate - (furoLength + 1) * furoWidth - 2 * displayWidth0 * scale;
                group = this.add.group();
                this.#furo[who][key] = group;
                [frameIndexList, kuiPos, extra] = this.parseFuro(who, tileIdList, [kuiTile, fromWho]);
                frameIndexList.forEach((item, index) => {
                    if (index === kuiPos) {
                        if (extra !== null) {
                            group.create(x + tileWidth0 * scale, y, imageSet1, extra).setOrigin(0, 0).setScale(scale).setDepth(y);
                        }
                        [kuiFinalX, kuiFinalY] = [x, y];
                        if (kuiX !== undefined) {
                            kuiTile = group.create(kuiX, kuiY, imageSet1, item).setOrigin(0, 0).setScale(scale).setDepth(y).setAlpha(0);
                        } else {
                            kuiTile = group.create(kuiFinalX, kuiFinalY, imageSet1, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                        }
                        y += tileHeight0 * scale;
                    } else {
                        if (item === 30) {
                            group.create(x, y, imageSet2, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                        }
                        else {
                            group.create(x, y, imageSet0, item).setOrigin(0, 0).setScale(scale).setDepth(y);
                        }
                        y += tileWidth1 * scale;
                    }
                })
        }
        this.tweens.add({
            targets: kuiTile,
            x: kuiFinalX,
            y: kuiFinalY,
            alpha: 1,
            duration: 200,
            ease: 'Power2'
        });
    }

    addKan(seat, who, pattern, add) {
        let furos = this.#furo[who];
        let scale = 0.5 * globalScaleRate;
        let ponGroup = furos[[1, pattern]];
        if (ponGroup === undefined) return;
        let ponTiles = ponGroup.getChildren();
        let relativePos = mod(who - seat, 4);
        let posList, kuiPos;
        let deltaX, deltaY;
        let kuiX, kuiY;
        let imageSet;
        let frameIndex = this.getTileFrameIndex(add);
        let addTile;
        let targetX, targetY;
        let moveDis = 100;
        switch (relativePos) {
            case 0:
                imageSet = 'tiles1';
                posList = ponTiles.map((child) => {
                    return child.width;
                });
                deltaX = 0;
                deltaY = - tileWidth1 * scale;
                kuiPos = argMax(posList);
                kuiX = ponTiles[kuiPos].x;
                kuiY = ponTiles[kuiPos].y;
                targetX = kuiX + deltaX;
                targetY = kuiY + deltaY;
                ponTiles[kuiPos].setDepth(1);
                addTile = ponGroup.create(targetX, targetY - moveDis * scale, imageSet, frameIndex).setOrigin(0, 0).setScale(scale);
                break
            case 1:
                imageSet = 'tiles2';
                posList = ponTiles.map((child) => {
                    return child.height;
                });
                deltaX = - displayWidth0 * scale;
                deltaY = 0;
                kuiPos = argMax(posList);
                kuiX = ponTiles[kuiPos].x;
                kuiY = ponTiles[kuiPos].y;
                targetX = kuiX + deltaX;
                targetY = kuiY + deltaY;
                addTile = ponGroup.create(targetX - moveDis * scale, targetY, imageSet, frameIndex).setOrigin(0, 0).setScale(scale).setDepth(targetY);
                break
            case 2:
                imageSet = 'tiles3';
                posList = ponTiles.map((child) => {
                    return child.width;
                });
                deltaX = 0;
                deltaY = tileWidth1 * scale;
                kuiPos = argMax(posList);
                kuiX = ponTiles[kuiPos].x;
                kuiY = ponTiles[kuiPos].y;
                targetX = kuiX + deltaX;
                targetY = kuiY + deltaY;
                addTile = ponGroup.create(targetX, targetY + moveDis * scale, imageSet, frameIndex).setOrigin(0, 0).setScale(scale).setDepth(targetY);
                break
            case 3:
                imageSet = 'tiles0';
                posList = ponTiles.map((child) => {
                    return child.height;
                });
                deltaX = displayWidth0 * scale;
                deltaY = 0;
                kuiPos = argMax(posList);
                kuiX = ponTiles[kuiPos].x;
                kuiY = ponTiles[kuiPos].y;
                targetX = kuiX + deltaX;
                targetY = kuiY + deltaY;
                addTile = ponGroup.create(targetX + moveDis * scale, targetY, imageSet, frameIndex).setOrigin(0, 0).setScale(scale).setDepth(targetY);
                break
        }
        this.tweens.add({
            targets: addTile,
            x: targetX,
            y: targetY,
            duration: 200,
            ease: 'Power2'
        });
    }

    renderSettlementDialog(observer, countdown) {
        if (document.hasFocus()) this.#settlementSound.play();
        let centerX = this.sys.canvas.width / 2;
        let centerY = this.sys.canvas.height / 2;
        let dialogWidth = 750 * globalScaleRate;
        let dialogHeight = 600 * globalScaleRate;
        let background = this.add.graphics();
        background.fillStyle(0x000000, 0.7);
        background.fillRoundedRect(centerX - dialogWidth / 2, centerY - dialogHeight / 2, dialogWidth, dialogHeight, 20 * globalScaleRate).setDepth(1500);

        this.#settlement.add(background);

        let btnWidth = 240 * globalScaleRate;
        let btnHeight = 80 * globalScaleRate;
        let button = this.add.graphics();
        button.fillStyle(0x000000, 0.7);
        button.lineStyle(globalScaleRate, 0xffffff, 1);

        button.fillRoundedRect(centerX - btnWidth / 2, centerY + dialogHeight / 2 - btnHeight - 20 * globalScaleRate, btnWidth, btnHeight, 10 * globalScaleRate).setDepth(1500);
        button.strokeRoundedRect(centerX - btnWidth / 2, centerY + dialogHeight / 2 - btnHeight - 20 * globalScaleRate, btnWidth, btnHeight, 10 * globalScaleRate).setDepth(1500);
        let buttonText = this.add.text(centerX, centerY + dialogHeight / 2 - btnHeight / 2 - 20 * globalScaleRate, 'OK', {
            fontFamily: 'Arial',
            fontSize: 40 * globalScaleRate + 'px',
            color: '#ffffff',
            stroke: '#000000',
            strokeThickness: 3 * globalScaleRate,
            shadow: {
                offsetX: 2 * globalScaleRate,
                offsetY: 2 * globalScaleRate,
                color: '#fff',
                blur: 2 * globalScaleRate,
                stroke: true,
                fill: true
            }
        }).setOrigin(0.5, 0.5).setDepth(1500);
        button.setInteractive(new Phaser.Geom.Rectangle(centerX - btnWidth / 2, centerY + dialogHeight / 2 - btnHeight - 20 * globalScaleRate, btnWidth, btnHeight), Phaser.Geom.Rectangle.Contains);
        button.on('pointerover', function (pointer) {
            pointer.event.target.style.cursor = 'pointer';
            this.alpha = 0.7;
        });
        button.on('pointerout', function (pointer) {
            pointer.event.target.style.cursor = 'default';
            this.alpha = 1;
        });
        let countdownText = this.add.text(centerX + btnWidth / 2 - 15 * globalScaleRate, centerY + dialogHeight / 2 - 30 * globalScaleRate, countdown, { fontSize: 20 * globalScaleRate + 'px', fill: '#fff' }).setOrigin(0.5, 0.5).setDepth(1500);
        this.#settlement.addMultiple([button, buttonText, countdownText]);
        button.on('pointerdown', (pointer) => {
            this.#settlement.clear(true, true);
            timer.destroy();
            pointer.event.target.style.cursor = 'default';
            if (!observer) this.#wsFcn({'event': 'ready'});
            alert('等待他人响应...');
        });
        let timer = this.time.addEvent({
            delay: 1000,
            callback: () => {
                countdown--;
                countdownText.setText(countdown.toString());
                if (countdown === -1) {
                    this.#settlement.clear(true, true);
                    timer.destroy();
                    this.input.setDefaultCursor('default');
                    if (!observer) this.#wsFcn({'event': 'ready'});
                }
            },
            loop: true
        });
    }

    renderScoreDelta(seat, oya, userInfo, scoreDelta) {
        let textStyle = {
            color: 'white',
            fontSize: 24 * globalScaleRate + 'px',
            fontFamily: 'Arial',
            stroke: '#fff',
            richText: true,
            align: 'center'
        };
        let x, y;
        let centerX = this.sys.canvas.width / 2;
        let centerY = this.sys.canvas.height / 2;
        for (let i = 0; i < 4; i++){
            let who = (seat + i) % 4;
            let [u, s] = userInfo[who];
            let ds = scoreDelta[who];
            let text;
            let wind = ['東', '南', '西', '北'][mod(who - oya, 4)];
            text = wind + '  ' + u + '\n' + s * 100;
            if (ds > 0) {
                text +=  '(+' + ds * 100 + ')';
            } else if (ds < 0) {
                text += '(' + ds * 100 + ')';
            }
            switch (i) {
                case 0:
                    x = centerX;
                    y = centerY + 150 * globalScaleRate;
                    break
                case 1:
                    x = centerX + 200 * globalScaleRate;
                    y = centerY + 90 * globalScaleRate;
                    break
                case 2:
                    x = centerX;
                    y = centerY + 30 * globalScaleRate;
                    break
                case 3:
                    x = centerX - 200 * globalScaleRate;
                    y = centerY + 90 * globalScaleRate;
                    break
            }
            text = this.add.text(x, y, text, textStyle).setOrigin(0.5).setDepth(1500);
                    this.#settlement.add(text);
        }
    }

    renderAgari(seat, oya, agariEvents, dora, uraDora, userInfo, scoreDelta, observer) {
        this.#settlement.clear(true, true);
        let width = this.sys.canvas.width;
        let height = this.sys.canvas.height;
        let centerX = width / 2;
        let centerY = height / 2;
        this.renderSettlementDialog(observer, 14);
        let yakuStyle = {
            fontSize: 30 * globalScaleRate + 'px',
            fontFamily: 'Kai',
            color: '#ffffff',
            align: 'center',
            lineSpacing: 15 * globalScaleRate
        };

        let pageContents = [];
        let textObjects = [];

        let titleStyle = {
            fontSize: 40 * globalScaleRate + 'px',
            fontFamily: 'Kai',
            color: '#ffffff',
            align: 'center'
        }

        agariEvents.forEach((action) => {
            let pageContent = [];
            let who = action["who"];
            let username = userInfo[who][0];
            let ret = action['yaku'];
            let yaku = action['yaku_list'];
            let han = action['han'];
            let fu = action['fu'];
            let score = action['score'];
            let text = username + ': ';
            if (Array.isArray(ret)) {
                if (han > 2) {
                    text += han + '倍役满';
                } else {
                    text += '役满';
                }
            } else {
                text += han + '番(' + fu + '符)';
                if (han === 5 || (han === 4 && fu >= 40) || (han === 3 && fu >= 70)) {
                    text += '(满贯)';
                } else {
                    switch (han) {
                        case 1:
                        case 2:
                        case 3:
                        case 4:
                            break
                        case 6:
                        case 7:
                            text += '(跳满)';
                            break
                        case 8:
                        case 9:
                        case 10:
                            text += '(倍满)';
                            break
                        case 11:
                        case 12:
                            text += '(三倍满)';
                            break
                        default:
                            text += '(累计役满)';
                    }
                }
            }
            text += ': ' + score + '点';
            pageContent.push({
                'text': text,
                'style': titleStyle,
                'x': centerX,
                'y': centerY - 250 * globalScaleRate
            });
            let yakuSlices = splitArray(yaku);
            let cols = yakuSlices.length;
            let interval = 750 * globalScaleRate / (cols + 1);
            let startX = (width - (750 * globalScaleRate)) / 2;
            yakuSlices.forEach((slice, index) => {
                pageContent.push({
                    'text': slice.join('\n'),
                    'style': yakuStyle,
                    'x': startX + interval * (index + 1),
                    'y': centerY - 130 * globalScaleRate
                })
            })
            pageContents.push(pageContent);
        });

        let currentPage = 0;

        let that = this;
        function displayPage(pageIndex) {
            textObjects.forEach(text => text.destroy());
            textObjects = [];
            pageContents[pageIndex].forEach(item => {
                let text = that.add.text(item['x'], item['y'], item['text'], item['style']).setOrigin(0.5, 0.5).setDepth(1500);
                that.#settlement.add(text);
                textObjects.push(text);
            })
        }
        if (pageContents.length > 1) {
            const rightTriangle = this.add.polygon(width - 100 * globalScaleRate, centerY, [0, 0, 30, 40, 0, 80].map((i)=>(i * globalScaleRate)), 0xffffff).setDepth(1500).setInteractive();
            rightTriangle.on('pointerover', (pointer) => {
                pointer.event.target.style.cursor = 'pointer';
                currentPage++;
                rightTriangle.setAlpha(0.5);
                if (currentPage > pageContents.length - 1) currentPage = agariEvents.length - 1;
                else displayPage(currentPage);
            });
            rightTriangle.on('pointerout', (pointer) => {
                rightTriangle.setAlpha(1);
                pointer.event.target.style.cursor = 'default';
            });


            const leftTriangle = this.add.polygon(100 * globalScaleRate, centerY, [30, 0, 0, 40, 30, 80].map((i)=>(i * globalScaleRate)), 0xffffff).setDepth(1500).setInteractive();
            leftTriangle.on('pointerover', (pointer) => {
                pointer.event.target.style.cursor = 'pointer';
                currentPage--;
                leftTriangle.setAlpha(0.5);
                if (currentPage < 0) currentPage = 0;
                else displayPage(currentPage);
            });
            leftTriangle.on('pointerout', (pointer) => {
                leftTriangle.setAlpha(1);
                pointer.event.target.style.cursor = 'default';
            });

            this.#settlement.addMultiple([leftTriangle, rightTriangle]);
        }

        displayPage(currentPage);

        dora = dora.map(this.getTileFrameIndex);
        uraDora = uraDora.map(this.getTileFrameIndex);
        dora = dora.concat(Array(5 - dora.length).fill(30));
        uraDora = uraDora.concat(Array(5 - uraDora.length).fill(30));
        let scale = 0.5 * globalScaleRate;
        let x = centerX - 320 * globalScaleRate;
        let y = centerY + 240 * globalScaleRate;
        dora.forEach((item) => {
            this.#settlement.create(x, y, 'tiles0', item).setScale(scale).setOrigin(0.5).setDepth(1500);
            x += scale * displayWidth0;
        });
        x = centerX + 320 * globalScaleRate - 4 * scale * displayWidth0;
        uraDora.forEach((item) => {
            this.#settlement.create(x, y, 'tiles0', item).setScale(scale).setOrigin(0.5).setDepth(1500);
            x += scale * displayWidth0;
        });
        this.renderScoreDelta(seat, oya, userInfo, scoreDelta);
    }

    renderRyuukyoku(seat, oya, ryuukyokuEvent, userInfo, scoreDelta, observer) {
        this.#settlement.clear(true, true);
        let centerX = this.sys.canvas.width / 2;
        let centerY = this.sys.canvas.height / 2;

        let titleStyle = {
            fontSize: 50 * globalScaleRate + 'px',
            fontFamily: 'Kai',
            color: '#ffffff',
            align: 'center'
        };
        let textStyle = {
            fontSize: 30 * globalScaleRate + 'px',
            fontFamily: 'Kai',
            color: '#ffffff',
            align: 'center'
        };
        this.renderSettlementDialog(observer, 14);
        let title;
        let nagashimanganText = '';
        let wind, who, u;
        switch (ryuukyokuEvent['why']) {
            case 'yama_end':
                title = '荒牌流局';
                let nagashimangan = ryuukyokuEvent['nagashimangan'];
                nagashimangan.forEach((key) => {
                    wind = ['東', '南', '西', '北'][mod(key - oya, 4)];
                    u = userInfo[key][0];
                    nagashimanganText += wind + ' ' + u + ': 流局满贯';
                });
                break
            case 'kaze4':
                title = '四风连打';
                break
            case 'ron3':
                title = '三家和了';
                break
            case 'reach4':
                title = '四家立直';
                break
            case 'kan4':
                title = '四杠散了';
                break
            case 'yao9':
                who = ryuukyokuEvent['who'];
                u = userInfo[who][0];
                title = u + ': 九种九牌';
                break

        }

        title = this.add.text(centerX, centerY - 230 * globalScaleRate, title, titleStyle).setOrigin(0.5, 0.5).setDepth(1500);
        this.#settlement.add(title);

        if (nagashimanganText !== '') {
            nagashimanganText = this.add.text(centerX, centerY - 120 * globalScaleRate, nagashimangan, textStyle).setOrigin(0.5, 0.5).setDepth(1500);
            this.#settlement.add(nagashimanganText);
        }

        this.renderScoreDelta(seat, oya, userInfo, scoreDelta);
    }

    renderDecisions(actions) {
        if (document.hasFocus()) this.#decisionSound.play();
        let actionsGroup = this.add.group();
        let actionDict = {'chi': [], 'pon': [], 'kan': [], 'ryuukyoku': [], 'agari': [], 'riichi': [], 'pass': []};
        actions.forEach(item => {
           actionDict[item['type']].push(item);
        });
        let availableActions = Object.entries(actionDict).filter(
            ([key, value]) => !(value.length === 0)
        )
        actionDict = Object.fromEntries(availableActions);
        let buttonCount = availableActions.length;
        let width = this.sys.canvas.width;
        let height = this.sys.canvas.height;
        let buttonWidth = 120 * globalScaleRate;
        let buttonHeight = 80 * globalScaleRate;
        let interval = 30 * globalScaleRate;
        let x = width - (buttonWidth + interval) * buttonCount + interval;
        let y = height - 180 * globalScaleRate;
        let textStyle = {
            fontSize: 35 * globalScaleRate + 'px',
            fontFamily: 'Kai',
            color: '#ffffff'
        }
        Object.entries(actionDict).forEach(([key, value]) => {
            let text;
            switch (key) {
                case 'pass':
                    text = 'Pass';
                    break;
                case 'chi':
                    text = '吃';
                    break;
                case 'pon':
                    text = '碰';
                    break;
                case 'kan':
                    text = '杠';
                    break;
                case 'riichi':
                    text = '立直';
                    break;
                case 'agari':
                    text = '和';
                    break;
                case 'ryuukyoku':
                    text = '流局';
                    break;
            }
            let square = this.add.rectangle(x, y, buttonWidth, buttonHeight, 0x222222).setAlpha(0.5).setDepth(1000).setInteractive();
            text = this.add.text(x, y, text, textStyle).setOrigin(0.5).setDepth(1000);
            actionsGroup.addMultiple([square, text]);
            square.on('pointerover', () => {
                this.input.setDefaultCursor('pointer');
                square.setAlpha(0.3);
            });
            square.on('pointerout', () => {
                this.input.setDefaultCursor('default');
                square.setAlpha(0.5);
            });
            if (value.length === 1) {
                square.on('pointerdown', () => {
                    this.queue.enqueue(value[0]);
                    this.input.setDefaultCursor('default');
                    actionsGroup.clear(true, true);
                });
            } else {
                let subY = y - 90 * globalScaleRate;
                let subButtonItems = [];
                value.forEach(item => {
                   let ptn = item['pattern'];
                   if (key === 'kan') {
                       ptn = [ptn[1] * 4 + 1];
                   }
                   let subSquare = this.add.rectangle(x, subY, buttonWidth, buttonHeight, 0x222222).setVisible(false).setAlpha(0.5).setDepth(1000).setInteractive();
                   subSquare.on('pointerdown', () => {
                       if (!subSquare.visible) return;
                       this.queue.enqueue(item);
                       this.input.setDefaultCursor('default');
                       actionsGroup.clear(true, true);
                    });
                   subSquare.on('pointerover', () => {
                       if (!subSquare.visible) return;
                        this.input.setDefaultCursor('pointer');
                        subSquare.setAlpha(0.3);
                    });
                   subSquare.on('pointerout', () => {
                       if (!subSquare.visible) return;
                        this.input.setDefaultCursor('default');
                        subSquare.setAlpha(0.5);
                    });
                   actionsGroup.add(subSquare);
                   subButtonItems.push(subSquare);
                   let tileX = x - 30 * globalScaleRate * (ptn.length - 1) / 2;
                   ptn.map(this.getTileFrameIndex).forEach((item) => {
                      let tile = actionsGroup.create(tileX, subY, 'tiles4', item).setVisible(false).setOrigin(0.5).setDepth(1000).setScale(0.25 * globalScaleRate);
                      subButtonItems.push(tile);
                      tileX += 30 * globalScaleRate;
                   });
                   subY -= (buttonHeight + 10 * globalScaleRate);
                });
                square.on('pointerdown', () => {
                    subButtonItems.forEach(item => {
                        if (item.visible) item.setVisible(false);
                        else item.setVisible(true);
                    });
                });
            }
            x += buttonWidth + interval;
        });
    }

    renderFinalScore(usernames, scores, observer) {
        this.#settlement.clear(true, true);
        let centerX = this.sys.canvas.width / 2;
        let centerY = this.sys.canvas.height / 2;
        this.renderSettlementDialog(observer, 9);
        let titleStyle = {
            fontSize: 50 * globalScaleRate + 'px',
            fontFamily: 'Kai',
            color: '#ffffff',
            align: 'center'
        };
        let title = this.add.text(centerX, centerY - 250 * globalScaleRate, '游戏结束', titleStyle).setOrigin(0.5).setDepth(1500);
        this.#settlement.add(title);

        let textStyle = {
            fontSize: 30 * globalScaleRate + 'px',
            fontFamily: 'Kai',
            color: '#ffffff',
            align: 'left',
            lineSpacing: 40 * globalScaleRate,
        };
        let y = centerY - 60 * globalScaleRate;
        let ranks = ['1st', '2nd', '3rd', '4th'];
        let text = ''
        scores.forEach(([who, score], index) => {
            let u = usernames[who];
            text += '\n' + ranks[index] + '、' + u + ': ' + score * 100;
        });
        text = this.add.text(centerX, y, text, textStyle).setOrigin(0.5).setDepth(1500);
        this.#settlement.add(text);
    }

    create () {
        let background = this.add.image(0, 0, 'background').setOrigin(0, 0);
        background.displayWidth = this.sys.canvas.width;
        background.displayHeight = this.sys.canvas.height;

        scene = this.scene.get('MahjongScene');
        this.#handTiles = this.add.group();
        this.#rightHand = this.add.group();
        this.#oppoHand = this.add.group();
        this.#leftHand = this.add.group();
        this.#gameInfo = this.add.group();
        this.#playerInfo = [this.add.group(), this.add.group(), this.add.group(), this.add.group()];
        this.#leftTileCount = this.add.group();
        this.#riichiBa = this.add.group();
        this.#yellowBars = this.add.group();
        this.#dora = this.add.group();
        this.#river = [this.add.group(), this.add.group(), this.add.group(), this.add.group()];
        this.#furo = [{}, {}, {}, {}];
        this.#settlement = this.add.group();
        this.#wsFcn = () => {};
        this.#drawSound = this.sound.add('draw_sound');
        this.#discardSound = this.sound.add('discard_sound');
        this.#decisionSound = this.sound.add('decision_sound');
        this.#settlementSound = this.sound.add('settlement_sound');

        this.#chiSound = [this.sound.add('chi_sound0'), this.sound.add('chi_sound1')];
        this.#ponSound = [this.sound.add('pon_sound0'), this.sound.add('pon_sound1')];
        this.#kanSound = [this.sound.add('kan_sound0'), this.sound.add('kan_sound1')];
        this.#ronSound = [this.sound.add('ron_sound0'), this.sound.add('ron_sound1')];
        this.#tsumoSound = [this.sound.add('tsumo_sound0'), this.sound.add('tsumo_sound1')];
        this.#riichiSound = [this.sound.add('riichi_sound0'), this.sound.add('riichi_sound1')];
        this.#wRiichiSound = [this.sound.add('w_riichi_sound0'), this.sound.add('w_riichi_sound1')];

        // this.renderGameInfo(2, 5);
        // this.renderPlayerInfo(0, 0, 'user1', 25000, 0);
        // this.renderPlayerInfo(0, 1, 'user2', 25000, 0);
        // this.renderPlayerInfo(0, 2, 'user3', 25000, 0);
        // this.renderPlayerInfo(0, 3, 'user4', 25000, 0);
        //
        // this.renderLeftTileCount(4);
        // this.renderRiichiBa(3);
        // this.renderDora([0, 1]);
        // this.renderHand([10, 11, 12, 13, 103, 102, 104, 105, 106, 107, 108, 109, 110]);
        // this.renderDraw(0, 0, 111)
        // this.renderLeftHand(7);
        // this.renderOthersOpenHand(0, 3, 7);
        // this.renderRightHand(10);
        // this.renderDraw(0, 1, 1, false)
        // this.renderDraw(0, 3, 1, false)
        // this.renderOthersOpenHand(0, 1, 11, true);
        // this.renderOthersOpenHand(0, 3, 8, true);
        // this.renderOppoHand(7);
        // this.renderDraw(0, 1)
        // for (let i of [1,2,10]){
        //     this.renderDraw(0, 0, i, false);
        // }
        // setTimeout(()=>{
        //     this.renderDraw(0, 3);
        // },500)
        // this.toggleBlink(0);
        // this.renderRiver(0, 0, [0,4,8,12,16,20,24,28,32,0,4,8,12,16,20,24], 24);
        // this.renderRiver(0, 1, [36,40,44,48,52,56,60,64,68,36,40], 60);
        // this.renderRiver(0, 2, [0,4,8,12,16,20,24,28,32,0,4,8,12,16,20,24,28], 28);
        // this.renderRiver(0, 3, [36,40,44,48,52,56,60,64,68,36,40,44,48,52,56,60,64], 64);
        // this.addRiver(0, 1, 123, 507.27199100112495, 805.6872890888638, false);
        // this.renderAction(0, 0, '碰');
        // this.renderFuriten(true);
        // this.addFuro(0, 3, 1, [113, 114, 112], 112, 1);
        // this.addKan(0,1,28,115);
        // this.renderDecisions([
        //     {'type': 'pass'},
        //     {'type': 'chi', 'pattern': [0, 4, 8], 'who': 0, 'from_who': 3, 'kui': 8},
        //     {'type': 'chi', 'pattern': [4, 8, 12], 'who': 0, 'from_who': 3, 'kui': 8},
        //     {'type': 'pon', 'pattern': [8, 9, 10], 'who': 0, 'from_who': 3, 'kui': 8},
        //     {'type': 'kan', 'pattern': [1, 2, 8], 'who': 0, 'from_who': 3, 'kui': 8},
        // ]);
        // this.renderFinalScore(['一姬', '一姬2', '一姬3', '一姬4'], [[1, 350], [0, 260], [2, 240], [3, 150]]);
    }
    resize(width, height) {
    }
}


let config = {
    type: Phaser.AUTO,
    antialias: true,
    width: minDimension,  // 设置初始宽度
    height: minDimension,  // 设置初始高度
    resolution: window.devicePixelRatio,
    scale: {
        mode: Phaser.Scale.FIT,  // 适应窗口大小，但保持游戏比例不变
        autoCenter: Phaser.Scale.CENTER_BOTH  // 游戏内容居中显示
    },
    scene: [MahjongScene],
    disableVisibilityChange: true,
    forceSetTimeOut: true
};

let game = new Phaser.Game(config);