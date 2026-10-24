import hashlib,json
import pytest
from scripts.curate_library import plan

def fixture(tmp_path):
    p=tmp_path/'models/a.json';p.parent.mkdir();p.write_text('{"id":"a"}')
    action={'file':'models/a.json','id':'a','action':'retire','before_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    return p,action

def test_plan_refuses_changed_data_and_does_not_touch_it(tmp_path):
    p,a=fixture(tmp_path);p.write_text('{"id":"a","user_edit":true}')
    before=p.read_bytes()
    with pytest.raises(ValueError,match='changed since review'):plan(tmp_path,{'actions':[a]})
    assert p.read_bytes()==before

def test_plan_never_accepts_database_or_path_escape(tmp_path):
    p,a=fixture(tmp_path)
    for name in ('models.db','models/../private.json','/tmp/models/a.json'):
        with pytest.raises(ValueError):plan(tmp_path,{'actions':[{**a,'file':name}]})
    assert p.exists()

def test_plan_requires_replacement_identity_and_hash(tmp_path):
    p,a=fixture(tmp_path)
    payload='{"id":"different"}'
    with pytest.raises(ValueError,match='identity'):
        plan(tmp_path,{'actions':[{**a,'action':'replace','content':payload,'after_sha256':hashlib.sha256(payload.encode()).hexdigest()}]})
    assert p.read_text()=='{"id":"a"}'

def test_retirement_plan_is_read_only_and_rejects_duplicates(tmp_path):
    p,a=fixture(tmp_path)
    rows=plan(tmp_path,{'actions':[a]});assert len(rows)==1 and rows[0][2] is None
    with pytest.raises(ValueError,match='Duplicate'):plan(tmp_path,{'actions':[a,a]})
    assert p.exists()

def admission(file='models/new/c.json',ident='c',content=None):
    content=content if content is not None else json.dumps({'id':ident,'name':'Reviewed candidate'})
    return {'action':'create','file':file,'id':ident,'content':content,'after_sha256':hashlib.sha256(content.encode()).hexdigest()}


def invoke(tmp_path,monkeypatch,actions,apply=True,hook=None):
    import sys
    import scripts.curate_library as transaction
    manifest=tmp_path/'reviewed-manifest.json';manifest.write_text(json.dumps({'actions':actions}))
    backup=tmp_path/'transaction-backup'
    calls=[]
    def service(command,check):
        calls.append(command)
        if hook:hook(command)
    monkeypatch.setattr(transaction.subprocess,'run',service)
    argv=['curate_library','--app',str(tmp_path),'--manifest',str(manifest),'--backup',str(backup),'--service','test-modeler']
    if apply:argv.append('--apply')
    monkeypatch.setattr(sys,'argv',argv)
    transaction.main()
    return backup,calls


def test_create_plan_validates_content_hash_identity_and_duplicate_id_anywhere(tmp_path):
    p,old=fixture(tmp_path)
    action=admission()
    rows=plan(tmp_path,{'actions':[action]})
    assert rows[0][3] is None and rows[0][2]==action['content'].encode()
    assert not (tmp_path/action['file']).exists()
    for bad,pattern in [({**action,'after_sha256':'bad'},'hash'),
                        ({**action,'id':'wrong'},'identity'),
                        (admission(ident='a'),'identity already exists'),
                        (admission(content='[]'),'identity'),
                        (admission(content='not-json'),'valid JSON')]:
        with pytest.raises(ValueError,match=pattern):plan(tmp_path,{'actions':[bad]})
    deep=tmp_path/'models/user/private/model.json';deep.parent.mkdir(parents=True);deep.write_text('{"id":"nested-user"}')
    with pytest.raises(ValueError,match='identity already exists'):
        plan(tmp_path,{'actions':[admission(ident='nested-user')]})
    with pytest.raises(ValueError,match='identity already exists'):
        plan(tmp_path,{'actions':[admission('models/c.json'),admission('models/d.json')]})
    assert p.read_text()=='{"id":"a"}'


def test_create_existing_exact_destination_and_unsafe_paths_are_never_overwritten(tmp_path):
    p,old=fixture(tmp_path)
    with pytest.raises(ValueError,match='already exists'):
        plan(tmp_path,{'actions':[admission('models/a.json')]})
    for file in ['models/../c.json','models/a/../../c.json','models\\c.json','models/C:\\c.json','/models/c.json','models.db','models/c.txt']:
        with pytest.raises(ValueError):plan(tmp_path,{'actions':[admission(file)]})
    outside=tmp_path/'outside';outside.mkdir()
    (tmp_path/'models/link').symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError,match='symbolic links'):
        plan(tmp_path,{'actions':[admission('models/link/c.json')]})
    assert list(outside.iterdir())==[]
    assert p.read_text()=='{"id":"a"}'


def test_create_dry_run_is_read_only_and_does_not_stop_writer(tmp_path,monkeypatch):
    fixture(tmp_path)
    database=tmp_path/'models.db';database.write_bytes(b'private database bytes')
    backup,calls=invoke(tmp_path,monkeypatch,[admission()],apply=False)
    assert calls==[] and not backup.exists()
    assert not (tmp_path/'models/new').exists()
    assert database.read_bytes()==b'private database bytes'


def mixed_actions(tmp_path):
    p,retire=fixture(tmp_path)
    b=tmp_path/'models/b.json';b.write_text('{"id":"b","before":true}')
    content='{"id":"b","reviewed":true}'
    replace={'action':'replace','file':'models/b.json','id':'b','before_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'content':content,'after_sha256':hashlib.sha256(content.encode()).hexdigest()}
    return [retire,replace,admission()],p.read_bytes(),b.read_bytes()


def test_mixed_create_retire_replace_success_receipt_and_database_preservation(tmp_path,monkeypatch):
    actions,original_a,original_b=mixed_actions(tmp_path)
    db=tmp_path/'models.db';db.write_bytes(b'private-model-database')
    user=tmp_path/'models/user.json';user.write_text('{"id":"private-user","untouched":true}')
    original_user=user.read_bytes()
    backup,calls=invoke(tmp_path,monkeypatch,actions)
    assert not (tmp_path/'models/a.json').exists()
    assert (tmp_path/'models/b.json').read_text()==actions[1]['content']
    assert (tmp_path/actions[2]['file']).read_text()==actions[2]['content']
    assert (backup/'models/a.json').read_bytes()==original_a
    assert (backup/'models/b.json').read_bytes()==original_b
    assert not (backup/actions[2]['file']).exists()
    receipt=json.loads((backup/'receipt.json').read_text())
    assert (receipt['retired'],receipt['replaced'],receipt['created'])==(1,1,1)
    assert receipt['created_files']==json.loads((backup/'created-files.json').read_text())
    assert receipt['created_files'][0]['after_sha256']==actions[2]['after_sha256']
    assert calls==[['systemctl','stop','test-modeler'],['systemctl','start','test-modeler']]
    assert db.read_bytes()==b'private-model-database' and user.read_bytes()==original_user
    assert not list((tmp_path/'models').rglob('*.curation*'))


def test_create_rechecks_existing_destination_race_after_writer_stop(tmp_path,monkeypatch):
    fixture(tmp_path)
    action=admission('models/c.json')
    def race(command):
        if command[1]=='stop':(tmp_path/action['file']).write_text('{"id":"late-user"}')
    with pytest.raises(ValueError,match='already exists'):
        invoke(tmp_path,monkeypatch,[action],hook=race)
    assert (tmp_path/action['file']).read_text()=='{"id":"late-user"}'
    assert not (tmp_path/'transaction-backup').exists()


def test_create_rechecks_duplicate_id_race_after_writer_stop(tmp_path,monkeypatch):
    fixture(tmp_path)
    def race(command):
        if command[1]=='stop':(tmp_path/'models/late.json').write_text('{"id":"c"}')
    with pytest.raises(ValueError,match='identity already exists'):
        invoke(tmp_path,monkeypatch,[admission()],hook=race)
    assert (tmp_path/'models/late.json').read_text()=='{"id":"c"}'
    assert not (tmp_path/'models/new/c.json').exists()


def test_atomic_create_never_overwrites_file_arriving_at_publication(tmp_path,monkeypatch):
    import os
    import scripts.curate_library as transaction
    fixture(tmp_path)
    original_link=os.link
    def race(src,dst,**kwargs):
        fd=os.open(dst,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644,dir_fd=kwargs['dst_dir_fd'])
        os.write(fd,b'{"id":"racing-user","value":17}');os.close(fd)
        return original_link(src,dst,**kwargs)
    monkeypatch.setattr(transaction.os,'link',race)
    with pytest.raises(FileExistsError):invoke(tmp_path,monkeypatch,[admission()])
    assert (tmp_path/'models/new/c.json').read_text()=='{"id":"racing-user","value":17}'
    assert not list((tmp_path/'models').rglob('*.curation*'))


def test_mixed_transaction_rollback_deletes_only_exact_created_hash(tmp_path,monkeypatch):
    import scripts.curate_library as transaction
    actions,original_a,original_b=mixed_actions(tmp_path)
    db=tmp_path/'models.db';db.write_bytes(b'original-db')
    original_hashes=transaction.data_hashes;calls=0
    def fail_final(app):
        nonlocal calls
        calls+=1
        if calls==2:raise RuntimeError('injected transaction verification failure')
        return original_hashes(app)
    monkeypatch.setattr(transaction,'data_hashes',fail_final)
    with pytest.raises(RuntimeError,match='injected'):
        invoke(tmp_path,monkeypatch,actions)
    assert (tmp_path/'models/a.json').read_bytes()==original_a
    assert (tmp_path/'models/b.json').read_bytes()==original_b
    assert not (tmp_path/actions[2]['file']).exists()
    assert db.read_bytes()==b'original-db'
    receipt=json.loads((tmp_path/'transaction-backup/rollback-receipt.json').read_text())
    assert not receipt['refused_unexpected_edits']
    assert actions[2]['file'] in receipt['restored_or_removed']


def test_rollback_preserves_external_created_file_edit_and_database_edit(tmp_path,monkeypatch):
    import scripts.curate_library as transaction
    actions,original_a,original_b=mixed_actions(tmp_path)
    db=tmp_path/'models.db';db.write_bytes(b'original-db')
    hashes=transaction.data_hashes;calls=0
    def foreign_edit(app):
        nonlocal calls
        calls+=1
        if calls==2:
            (tmp_path/actions[2]['file']).write_text('{"id":"c","external_edit":true}')
            db.write_bytes(b'external-db-edit')
        return hashes(app)
    monkeypatch.setattr(transaction,'data_hashes',foreign_edit)
    with pytest.raises(RuntimeError,match='Refusing rollback'):
        invoke(tmp_path,monkeypatch,actions)
    assert (tmp_path/actions[2]['file']).read_text()=='{"id":"c","external_edit":true}'
    assert (tmp_path/'models/a.json').read_bytes()==original_a
    assert (tmp_path/'models/b.json').read_bytes()==original_b
    assert db.read_bytes()==b'external-db-edit'
    receipt=json.loads((tmp_path/'transaction-backup/rollback-receipt.json').read_text())
    assert receipt['refused_unexpected_edits']==[actions[2]['file']]


def test_duplicate_id_arriving_during_publish_causes_safe_rollback(tmp_path,monkeypatch):
    import os
    import scripts.curate_library as transaction
    fixture(tmp_path)
    original_link=os.link
    def race(src,dst,**kwargs):
        (tmp_path/'models/late-user.json').write_text('{"id":"c","user":true}')
        return original_link(src,dst,**kwargs)
    monkeypatch.setattr(transaction.os,'link',race)
    with pytest.raises(RuntimeError,match='Unexpected model/database'):
        invoke(tmp_path,monkeypatch,[admission()])
    assert not (tmp_path/'models/new/c.json').exists()
    assert (tmp_path/'models/late-user.json').read_text()=='{"id":"c","user":true}'

def test_create_id_inventory_includes_uppercase_json_files(tmp_path):
    fixture(tmp_path)
    (tmp_path/'models/user.JSON').write_text('{"id":"c"}')
    with pytest.raises(ValueError,match='identity already exists'):
        plan(tmp_path,{'actions':[admission()]})


def test_parent_symlink_race_cannot_create_outside_models(tmp_path,monkeypatch):
    import scripts.curate_library as transaction
    fixture(tmp_path)
    outside=tmp_path/'outside';outside.mkdir()
    original=transaction._create_parent
    def race(app,relative):
        (tmp_path/'models/new').symlink_to(outside,target_is_directory=True)
        return original(app,relative)
    monkeypatch.setattr(transaction,'_create_parent',race)
    with pytest.raises(OSError):invoke(tmp_path,monkeypatch,[admission()])
    assert list(outside.iterdir())==[]


def test_failure_immediately_after_atomic_publication_rolls_back_create(tmp_path,monkeypatch):
    import scripts.curate_library as transaction
    fixture(tmp_path)
    original=transaction.os.unlink;failed=False
    def fail_cleanup(path,*args,**kwargs):
        nonlocal failed
        if '.curation-' in str(path) and not failed:
            failed=True
            raise OSError('injected cleanup failure after publication')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(transaction.os,'unlink',fail_cleanup)
    with pytest.raises(OSError,match='injected cleanup failure'):
        invoke(tmp_path,monkeypatch,[admission()])
    assert not (tmp_path/'models/new/c.json').exists()
    assert not list((tmp_path/'models').rglob('*.curation*'))
    receipt=json.loads((tmp_path/'transaction-backup/rollback-receipt.json').read_text())
    assert receipt['restored_or_removed']==['models/new/c.json']


def test_backup_may_not_write_into_model_paths_or_database(tmp_path,monkeypatch):
    import sys
    import scripts.curate_library as transaction
    fixture(tmp_path)
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps({'actions':[admission()]}))
    def forbidden(*args,**kwargs):raise AssertionError('Writer must not stop')
    monkeypatch.setattr(transaction.subprocess,'run',forbidden)
    for backup in [tmp_path/'models/backup',tmp_path/'models.db']:
        monkeypatch.setattr(sys,'argv',['curate_library','--app',str(tmp_path),'--manifest',str(manifest),'--backup',str(backup),'--service','test-modeler','--apply'])
        with pytest.raises(ValueError,match='outside model data'):
            transaction.main()
        assert not backup.exists()

def test_create_rejects_nonfinite_or_bom_content_before_mutation(tmp_path):
    fixture(tmp_path)
    for text in ['{"id":"c","value":NaN}','{"id":"c","value":Infinity}','\ufeff{"id":"c"}']:
        with pytest.raises(ValueError,match='valid JSON'):
            plan(tmp_path,{'actions':[admission(content=text)]})
    assert not (tmp_path/'models/new').exists()

def test_preexisting_backup_is_never_modified_on_failure(tmp_path,monkeypatch):
    fixture(tmp_path)
    backup=tmp_path/'transaction-backup';backup.mkdir()
    sentinel=backup/'receipt.json';sentinel.write_text('previous transaction evidence')
    before={p.name:p.read_bytes() for p in backup.iterdir()}
    with pytest.raises(FileExistsError):invoke(tmp_path,monkeypatch,[admission()])
    assert {p.name:p.read_bytes() for p in backup.iterdir()}==before
    assert not (tmp_path/'models/new/c.json').exists()

def test_create_inventory_refuses_nonregular_json_without_blocking(tmp_path):
    import os
    from scripts.curate_library import digest
    fixture(tmp_path)
    fifo=tmp_path/'models/unexpected.json';os.mkfifo(fifo)
    with pytest.raises(ValueError,match='regular files'):
        plan(tmp_path,{'actions':[admission()]})
    with pytest.raises(ValueError,match='regular files'):
        digest(fifo)

def test_created_reviewed_model_is_readable_under_restrictive_operator_umask(tmp_path,monkeypatch):
    import os
    fixture(tmp_path)
    existing=tmp_path/'models';existing.chmod(0o750)
    previous=os.umask(0o077)
    try:invoke(tmp_path,monkeypatch,[admission()])
    finally:os.umask(previous)
    assert (tmp_path/'models/new/c.json').stat().st_mode & 0o777 == 0o644
    assert (tmp_path/'models/new').stat().st_mode & 0o777 == 0o755
    assert existing.stat().st_mode & 0o777 == 0o750

def test_inventory_and_hash_snapshot_fail_closed_on_unreadable_subtree(tmp_path,monkeypatch):
    import scripts.curate_library as transaction
    fixture(tmp_path)
    hidden=tmp_path/'models/hidden';hidden.mkdir()
    (hidden/'duplicate.json').write_text('{"id":"c"}')
    original=transaction.os.scandir
    def unreadable(path):
        if str(path)==str(hidden):raise PermissionError('injected unreadable subtree')
        return original(path)
    monkeypatch.setattr(transaction.os,'scandir',unreadable)
    with pytest.raises(PermissionError,match='unreadable subtree'):
        plan(tmp_path,{'actions':[admission()]})
    with pytest.raises(PermissionError,match='unreadable subtree'):
        transaction.data_hashes(tmp_path)
    assert not (tmp_path/'models/new').exists()


def test_uppercase_json_foreign_edit_invalidates_receipt_and_preserves_edit(tmp_path,monkeypatch):
    import scripts.curate_library as transaction
    fixture(tmp_path)
    foreign=tmp_path/'models/legacy.JSON';foreign.write_text('{"id":"legacy"}')
    original=transaction.data_hashes;calls=0
    def edit_before_verification(app):
        nonlocal calls
        calls+=1
        if calls==2:foreign.write_text('{"id":"legacy","foreign_edit":true}')
        return original(app)
    monkeypatch.setattr(transaction,'data_hashes',edit_before_verification)
    with pytest.raises(RuntimeError,match='Unexpected model/database change'):
        invoke(tmp_path,monkeypatch,[admission()])
    assert json.loads(foreign.read_text())['foreign_edit'] is True
    assert not (tmp_path/'models/new/c.json').exists()
    assert not (tmp_path/'transaction-backup/receipt.json').exists()
