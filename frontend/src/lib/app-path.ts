export const appBasePath=process.env.NEXT_PUBLIC_BASE_PATH||'';
export function appPath(path:string){return path.startsWith('/')&&!path.startsWith('//')&&!path.startsWith(appBasePath+'/')?appBasePath+path:path;}
/** Prefix real same-origin requests; responses come from the server. */
export function appFetch(input:RequestInfo|URL,init?:RequestInit){return globalThis.fetch(typeof input==='string'?appPath(input):input,init);}
