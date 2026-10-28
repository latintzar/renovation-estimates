#!/usr/bin/env node
// Parse source only. No app/runtime modules are imported.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const root=path.resolve(process.argv[2]);
const require=createRequire(path.join(root,'frontend/package.json'));
const ts=process.argv[3]?require(path.resolve(process.argv[3])):require('typescript');
const rows=[];
function walk(dir){
  for(const entry of fs.readdirSync(dir,{withFileTypes:true})){
    const file=path.join(dir,entry.name);
    if(entry.isDirectory())walk(file);
    else if(/\.(ts|tsx)$/.test(entry.name)&&!entry.name.endsWith('.d.ts')){
      const text=fs.readFileSync(file,'utf8');
      const source=ts.createSourceFile(file,text,ts.ScriptTarget.Latest,true);
      const symbols=[];
      function visit(node,parent=''){
        const named=(ts.isFunctionDeclaration(node)||ts.isClassDeclaration(node)||ts.isInterfaceDeclaration(node)||ts.isTypeAliasDeclaration(node)||ts.isEnumDeclaration(node)||ts.isMethodDeclaration(node)||ts.isVariableDeclaration(node))&&node.name;
        let next=parent;
        if(named&&ts.isIdentifier(node.name)){
          const name=node.name.text;
          const kind=ts.SyntaxKind[node.kind];
          const qualified=parent?parent+'.'+name:name;
          const line=source.getLineAndCharacterOfPosition(node.getStart(source)).line+1;
          symbols.push({name:qualified,kind,line});
          if(ts.isClassDeclaration(node)||ts.isFunctionDeclaration(node))next=qualified;
        }
        ts.forEachChild(node,child=>visit(child,next));
      }
      visit(source);
      rows.push({path:path.relative(root,file).split(path.sep).join('/'),symbols});
    }
  }
}
walk(path.join(root,'frontend/src'));
process.stdout.write(JSON.stringify(rows));
