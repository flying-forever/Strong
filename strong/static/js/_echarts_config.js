// chartConfig.js
console.log(getAspectRatio(), window.innerWidth, window.innerHeight);

function getAspectRatio() {
    // 暂时没用到
    return window.innerWidth / window.innerHeight;
}

const commonMediaQuery = [
    {
        // 移动端更充分地占用屏幕，使用Height是用于被旋转的容器，用Weight横屏会很长
        query: { maxHeight: 1000 },
        option: {
            textStyle: {
                fontSize: '1.3rem',
            },
            title: {
                textStyle: { fontSize: '1.5rem' },
                subtextStyle: { fontSize: '1rem' },
            },
            xAxis: {
                axisLabel: { fontSize: '1rem' },
            },
            yAxis: {
                axisLabel: { fontSize: '1rem' },
            },
        },
        callback: function (mediaQuery) {
            console.log('Media query applied:', mediaQuery);
        },
    },
];

/**
 * 小屏幕竖屏设备旋转的横屏使用。要容器高小于x，实际宽小于x。
 * 
 * @param {Array} [specificMediaQueries=[]] - 你需要自定义添加的媒体查询列表
 */
function mergeMedia(specificMediaQueries = []) {
    // 小屏幕竖屏设备旋转的横屏使用。要容器高小于x，实际宽小于x。
    var filter = function (media) {
        m = media.map(item => {
            // 回调形式，为了对每个item打印信息
            var pass = window.innerWidth < item.query.maxHeight;
            r = {
                ...item,
                option: pass ? item.option : {}
            };
            console.log('[竖屏横用]', pass, 'window.innerWidth:', window.innerWidth, 'query:', item.query.maxHeight)
            return r
        });
        return m;
    }
    var media = filter(specificMediaQueries)
    var m0 = filter(commonMediaQuery)
    return m0.concat(media);
}
