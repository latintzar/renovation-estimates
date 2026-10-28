#!/usr/bin/env python3
"""Build a source-only Python AST / TypeScript compiler symbol reference."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'docs/reference'


def python_modules():
    rows=[]
    for file in sorted([* (ROOT/'backend').rglob('*.py'), * (ROOT/'tools').glob('*.py')]):
        text=file.read_text()
        tree=ast.parse(text)
        symbols=[]
        def visit(node,parent=''):
            for child in ast.iter_child_nodes(node):
                if isinstance(child,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
                    name=(parent+'.' if parent else '')+child.name
                    doc=(ast.get_docstring(child) or '').split('\n\n',1)[0].replace('\n',' ')[:280]
                    item={'name':name,'kind':type(child).__name__,'line':child.lineno,'summary':doc}
                    if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)):
                        item['parameters']=[a.arg for a in child.args.posonlyargs+child.args.args+child.args.kwonlyargs]
                    symbols.append(item)
                    visit(child,name)
                else:visit(child,parent)
        visit(tree)
        doc=(ast.get_docstring(tree) or '').split('\n\n',1)[0].replace('\n',' ')[:280]
        rows.append({'path':file.relative_to(ROOT).as_posix(),'summary':doc,'symbols':symbols})
    return rows


def build(compiler):
    command=['node',str(ROOT/'tools/source-reference.mjs'),str(ROOT)]
    if compiler:command.append(compiler)
    p=subprocess.run(command,capture_output=True,text=True,check=True)
    modules=python_modules()+json.loads(p.stdout)
    modules.sort(key=lambda x:x['path'])
    contents={}
    index=['# Source reference','', 'Generated from source with Python AST and the TypeScript compiler. Each module links to its source and every discovered named symbol. The generator executes no application code and records no literal default values.','']
    for group in sorted({x['path'].rsplit('/',1)[0] for x in modules}):
        index+=['## '+group,'']
        for item in [x for x in modules if x['path'].rsplit('/',1)[0]==group]:
            name=item['path']; destination=OUTPUT/'modules'/(name+'.md')
            relative_source=Path(__import__('os').path.relpath(ROOT/name,destination.parent)).as_posix()
            doc=['# '+name,'', '[Source]('+relative_source+')','']
            if item.get('summary'):doc+=[item['summary'],'']
            doc+=['| Symbol | Kind | Source line |','|---|---|---|']
            for symbol in item['symbols']:
                safe=symbol['name'].replace('|','\\|')
                doc+=['| `'+safe+'` | '+symbol['kind']+' | [L'+str(symbol['line'])+']('+relative_source+'#L'+str(symbol['line'])+') |']
            doc+=['']
            contents[destination]='\n'.join(doc)
            index+=['- ['+name+'](modules/'+name+'.md): '+str(len(item['symbols']))+' symbols.']
        index+=['']
    contents[OUTPUT/'README.md']='\n'.join(index)
    data={'schema_version':1,'source_commit':'4dca5f9bd94a3ee4759dff949f3d185acd095022','modules':modules}
    contents[OUTPUT/'symbols.json']=json.dumps(data,indent=2)+'\n'
    return contents,modules


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');parser.add_argument('--typescript-path');args=parser.parse_args()
    contents,modules=build(args.typescript_path)
    for existing in (OUTPUT/'modules').rglob('*.md'):
        if existing not in contents:
            if args.check:raise SystemExit('Source reference contains an obsolete module page.')
            existing.unlink()
    for file,text in contents.items():
        if args.check:
            if not file.exists() or file.read_text()!=text:raise SystemExit('Source reference needs regeneration: '+str(file.relative_to(ROOT)))
        else:file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text)
    print(json.dumps({'modules':len(modules),'symbols':sum(len(x['symbols']) for x in modules),'checked':args.check}))


if __name__=='__main__':main()
