const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const elements = {};
function element(id) {
  return elements[id] ??= {value:id==='frets'?'24':id==='tuning'?'Standard':'all',
    checked:false,options:[],style:{},dataset:{},children:[],
    add(o){this.options.push(o);if(this.options.length===1)this.value=o.value},
    replaceChildren(){this.options=[];this.children=[];this.value=''},
    append(o){this.children.push(o)},addEventListener(){},setAttribute(){},focus(){}};
}
const context = vm.createContext({document:{getElementById:element,
  querySelectorAll:()=>[],createElement:()=>({style:{},dataset:{},append(){},setAttribute(){}})},
  Option:function(text,value){this.text=text;this.value=value},fetch:()=>new Promise(()=>{}),
  structuredClone,cancelAnimationFrame(){},console});
const html=fs.readFileSync(path.join(__dirname,'../static/index.html'),'utf8');
vm.runInContext(html.split('<script>')[1].split('</script>')[0],context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/editor.js'),'utf8'),context);
vm.runInContext(`
file={name:'riff.mid'};presets={Standard:[40,45,50,55,59,64]};
data={tuning:presets.Standard,tuning_name:'Standard',tempo_map:[{beat:0,seconds:0,bpm:120},{beat:1,seconds:.5,bpm:60}],
notes:[{id:0,pitch:64,string:5,fret:0,beat:0,duration_beats:2,start:0,duration:1.5,velocity:100}],
source_notes:[],warnings:[],duration:1.5,total:1};
data.source_notes=structuredClone(data.notes);importEditor();
`,context);
assert.equal(element('bpm').value,'120.00');
element('bpm').value='240';element('bpm').onchange();
assert.equal(vm.runInContext('data.notes[0].duration',context),.75);
assert.equal(vm.runInContext('data.notes[0].beat',context),0);
vm.runInContext('openNote(0)',context);
element('editFret').value='5';element('editString').value='5';
element('editBeat').value='2';element('editLength').value='.5';element('editVelocity').value='75';
element('saveNote').onclick();
assert.equal(vm.runInContext('data.notes[0].pitch',context),69);
assert.equal(vm.runInContext('data.notes[0].start',context),.25);
assert.equal(vm.runInContext('data.notes[0].duration',context),.25);
assert.equal(vm.runInContext('data.source_notes[0].velocity',context),75);
vm.runInContext('data.notes.push({...data.notes[0],id:1});openNote(0)',context);
element('saveNote').onclick();
assert.ok(element('editError').textContent.includes('occupies'));
element('resetEdits').onclick();
assert.equal(vm.runInContext('data.notes[0].pitch',context),64);
assert.equal(vm.runInContext('data.notes[0].duration',context),1.5);
vm.runInContext('openNote(0)',context);element('deleteNote').onclick();
assert.equal(vm.runInContext('data.total',context),0);
assert.equal(element('play').disabled,true);
assert.equal(vm.runInContext('data.duration',context),0);
console.log('Editor checks passed: tempo map scaling, timing/pitch/velocity edits, string conflicts, reset, delete.');
