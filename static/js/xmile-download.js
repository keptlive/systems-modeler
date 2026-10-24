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
                    if(!response.ok) throw new Error('Check the model inputs before exporting.');
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