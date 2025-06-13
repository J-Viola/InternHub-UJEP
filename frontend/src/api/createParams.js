// z dict uděláme parametry do requestu
export const createParams = (dicts) => { 
    const searchParams = new URLSearchParams();

    Object.keys(dicts).forEach(key => {
        if (dicts[key] !== undefined && dicts[key] !== null && dicts[key] !== '') {
            searchParams.append(key, dicts[key]);
        }
    });

    return `?${searchParams.toString()}`;
};