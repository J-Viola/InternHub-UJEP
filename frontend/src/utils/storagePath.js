// A-24: CV a profilové fotky jsou chráněné — nelze je načíst přes <img src>/<a href> na /storage/
// (prohlížeč neposílá Authorization). Převedeme URL z API na chráněnou trasu /api/files/<rel>/.
export function storageUrlToApiPath(url) {
    if (!url || typeof url !== 'string') return null;
    let path = url;
    try {
        path = new URL(url, 'http://placeholder.local').pathname;
    } catch (e) {
        return null;
    }
    const match = path.match(/^\/storage\/(.+)$/);
    if (!match) return null;
    return `/files/${match[1]}/`;
}
