import { NextResponse, type NextRequest } from 'next/server';
import fixture from '@/fixtures/native-workspace.json';
import {nativeSampleResponse} from '@/lib/sample/response.mjs';
export function proxy(request: NextRequest) {
  const base=request.nextUrl.basePath||process.env.NEXT_PUBLIC_BASE_PATH||'';
  const path=base&&request.nextUrl.pathname===base?'/':base&&request.nextUrl.pathname.startsWith(base+'/')?request.nextUrl.pathname.slice(base.length):request.nextUrl.pathname;
  if(process.env.SAMPLE_MODE==='1'&&path.startsWith('/api/')){
    const result=nativeSampleResponse(fixture,path,request.method,request.nextUrl.searchParams,base);
    return NextResponse.json(result.body,{status:result.status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
  }
  if(path==='/'){
    const target=request.nextUrl.clone();const host=request.headers.get('x-forwarded-host')||request.headers.get('host');
    if(host&&!/[\\/@#?\s,]/.test(host))target.host=host;
    if(request.headers.get('x-forwarded-proto')==='https')target.protocol='https:';
    target.pathname='/listings';return NextResponse.redirect(target);
  }
  return NextResponse.next();
}
export const config = { matcher: ['/', '/((?!_next/static|_next/image|favicon.ico).*)'] };
