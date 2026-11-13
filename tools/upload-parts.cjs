// Transfer encrypted output one small artifact at a time, below the free quota.
const {DefaultArtifactClient}=require('@actions/artifact');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const client=new DefaultArtifactClient();
const repo=process.env.GITHUB_REPOSITORY;
const headers={Authorization:`Bearer ${process.env.GH_TOKEN}`,Accept:'application/vnd.github+json'};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function api(suffix){return fetch(`https://api.github.com/repos/${repo}/${suffix}`,{headers});}
(async()=>{
 const file=process.argv[2],fd=fs.openSync(file,'r'),size=fs.statSync(file).size;
 const chunkSize=128*1024*1024,deadline=Date.now()+3*3600*1000;
 const manifest={size,parts:[]};
 for(let offset=0,index=0;offset<size;index++){
  let used=0;
  for(let page=1;;page++){
   const response=await api(`actions/artifacts?per_page=100&page=${page}`);
   if(!response.ok)throw new Error(`artifact quota check ${response.status}`);
   const {artifacts}=await response.json();
   used+=artifacts.filter(a=>!a.expired).reduce((s,a)=>s+a.size_in_bytes,0);
   if(artifacts.length<100)break;
  }
  if(used+chunkSize>450*1024*1024)throw new Error('free artifact storage ceiling would be exceeded');
  const data=Buffer.alloc(Math.min(chunkSize,size-offset));
  if(fs.readSync(fd,data,0,data.length,offset)!==data.length)throw new Error('short input');
  const name=`ios-transfer-${String(index).padStart(3,'0')}`;
  const local=path.resolve('out',name+'.bin');fs.writeFileSync(local,data);
  manifest.parts.push({name,file:path.basename(local),sha256:crypto.createHash('sha256').update(data).digest('hex'),size:data.length});
  const {id}=await client.uploadArtifact(name,[local],path.resolve('out'),{retentionDays:1,compressionLevel:0});
  console.log(`Waiting for local receiver to acknowledge part ${index}, artifact ${id}`);
  for(;;){
   if(Date.now()>deadline)throw new Error('receiver timeout');
   const state=await api(`actions/artifacts/${id}`);
   if(state.status===404)break;
   if(!state.ok)throw new Error(`artifact poll ${state.status}`);
   await sleep(10000);
  }
  fs.unlinkSync(local);offset+=data.length;
 }
 fs.closeSync(fd);
 const p=path.resolve('out/transfer-manifest.json');fs.writeFileSync(p,JSON.stringify(manifest,null,2));
 await client.uploadArtifact('ios-transfer-complete',[p],path.resolve('out'),{retentionDays:1});
})().catch(e=>{console.error(e);process.exit(1)});
