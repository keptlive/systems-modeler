// Error bodies are untrusted: read a small bounded prefix and display text only.
async function xmileExportErrorMessage(response) {
    const fallback='XMILE export could not complete. Choose Download JSON to preserve all model settings.';
    const type=(response.headers?.get('content-type')||'').toLowerCase().split(';')[0].trim();
    const jsonType=type==='application/json'||type.endsWith('+json');
    if(!jsonType&&type!=='text/plain')return fallback;
    let reader;try{reader=response.body?.getReader?.();}catch(_){return fallback;}
    if(!reader)return fallback;
    let size=0,reads=0,text='',timer;const decoder=new TextDecoder(),deadline=Date.now()+2000;
    try {
        while(size<8192&&reads++<32){
            const remaining=deadline-Date.now();if(remaining<=0)return fallback;
            const part=await Promise.race([reader.read(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Error detail deadline')),remaining);})]);
            clearTimeout(timer);timer=null;if(part.done)break;
            const chunk=part.value.subarray(0,8192-size);size+=chunk.byteLength;
            text+=decoder.decode(chunk,{stream:true});
        }
        text+=decoder.decode();
    } catch (_) {return fallback;}
    finally {clearTimeout(timer);try{reader.cancel()?.catch(()=>{});}catch(_){}try{reader.releaseLock();}catch(_){}}
    let message;
    if(jsonType){
        try{const body=JSON.parse(text);message=typeof body.detail==='string'?body.detail:typeof body.failure?.message==='string'?body.failure.message:null;}catch(_){return fallback;}
    }else message=text;
    if(typeof message!=='string')return fallback;
    message=message.replace(/[\u0000-\u001f\u007f]/g,' ').replace(/\s+/g,' ').trim().slice(0,500);
    return message?message+' Choose Download JSON to preserve all model settings.':fallback;
}
// Export the current draft, including unsaved edits, without changing the library.
document.addEventListener('DOMContentLoaded', () => {
    const dialog=document.createElement('dialog');dialog.id='export-dialog';
    const title=document.createElement('h2');title.id='export-title';title.textContent='Export current model';
    dialog.setAttribute('aria-labelledby',title.id);dialog.appendChild(title);
    const help=document.createElement('p');help.textContent='Download a copy with your current equations, settings and sources.';dialog.appendChild(help);
    for (const format of ['XMILE','JSON']) {
        const button=document.createElement('button');button.textContent=`Download ${format}`;
        button.addEventListener('click',async()=>{
            button.disabled=true;
            try {
                let blob;
                if(format==='JSON') blob=new Blob([JSON.stringify(App.model,null,2)],{type:'application/json'});
                else {
                    const response=await fetch('/api/models/export/xmile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...App.model,id:App.model.id||'draft'})});
                    if(!response.ok) throw new Error(await xmileExportErrorMessage(response));
                    blob=await response.blob();
                }
                const link=document.createElement('a'),url=URL.createObjectURL(blob);
                link.href=url;link.download=(App.model.name||'model').replace(/[<>:"/\\|?*]/g,'_')+'.'+format.toLowerCase();
                document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);dialog.close();
            } catch(error) {alert('Export failed: '+error.message);} finally {button.disabled=false;}
        });
        dialog.appendChild(button);
    }
    const close=document.createElement('button');close.textContent='Cancel';close.addEventListener('click',()=>dialog.close());dialog.appendChild(close);
    document.body.appendChild(dialog);
    document.getElementById('btn-download').addEventListener('click',()=>dialog.showModal());
});