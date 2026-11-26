import pathlib,json,struct,hashlib,copy,uuid,re
import numpy as np,UnityPy
from scipy.spatial.transform import Rotation as Rot
from PIL import Image
from UnityPy.files.SerializedFile import FileIdentifier
P=pathlib.Path(__file__).resolve().parents[2];src=P/'Export';work=P/'SPT';pkg=work/'Package';base=pathlib.Path('E:/SPT 4.1.6/EscapeFromTarkov_Data/StreamingAssets/Windows')
native=json.loads((base/'Windows.json').read_text());tmp=pathlib.Path('E:/Temp/Justicar-RSh')
names=[x['path'].split('/')[-1] for x in json.loads((tmp/'rig.json').read_text())['nodes']];idle=np.fromfile(tmp/'samples/rsh12_idle_disarmed.bin','f').reshape(-1,len(names),4,4)[0]
G=np.array(json.loads((tmp/'layout.json').read_text())['G']); axes=G[:3,:3]@np.array([[1,0,0],[0,0,-1],[0,1,0]])
piv=json.loads((tmp/'piv.json').read_text())
def world(pos):return G[:3,:3]@pos+G[:3,3]
def xyz(v):return dict(zip('xyz',map(float,v)))
def pointer(id):return dict(m_FileID=0,m_PathID=id)
def readgl(f):
 data=f.read_bytes();l=struct.unpack_from('<I',data,12)[0];j=json.loads(data[20:20+l]);b=data[28+l:]
 def acc(ix):
  a=j['accessors'][ix];v=j['bufferViews'][a['bufferView']];sz={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];dt=np.dtype({5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}[a['componentType']]);return np.ndarray((a['count'],sz),dt,buffer=b,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',sz*dt.itemsize),dt.itemsize))
 ps=[];ns=[];uv=[];tri=[];groups=[];materials=[];counts=[]
 for pr in j['meshes'][0]['primitives']:
  counts.append(j['accessors'][pr['indices']]['count']);at=pr['attributes'];v=acc(at['POSITION']);tri.extend(acc(pr['indices']).reshape(-1,3)+sum(map(len,ps)));ps.append(v);ns.append(acc(at['NORMAL']));uv.append(acc(at['TEXCOORD_0']));materials.append(j['materials'][pr['material']]['name'])
  if 'JOINTS_0' in at:
   joints=np.array([j['nodes'][k]['name'] for k in j['skins'][0]['joints']]);g=acc(at['JOINTS_0'])[np.arange(len(v)),acc(at['WEIGHTS_0']).argmax(axis=1)];groups.extend(joints[g])
  else:groups.extend(['Body']*len(v))
 return dict(v=np.concatenate(ps),n=np.concatenate(ns),uv=np.concatenate(uv),tri=np.asarray(tri),groups=np.array(groups),mat=materials[0],material_names=materials,index_counts=counts,nodes={n.get('name'):n.get('translation',[0,0,0]) for n in j['nodes']})
geo={f.stem.split('TheJudge_')[-1]:readgl(f) for f in src.rglob('SK_WP_Revolver_TheJudge_*.glb') if not f.stem.endswith('_Rig')}
for f in (P/'Ammo').rglob('*.glb'):geo[f.stem]=readgl(f)
loader=next(src.rglob('SK_WP_Revolver_Justicar_SpeedLoader.glb'));geo['SpeedLoader']=readgl(loader)
materials={k:v['mat'] for k,v in geo.items()}
def build_textures(dest):
 dest.mkdir(parents=True,exist_ok=True)
 for mat in set(materials.values()):
  f=next(P.glob('**/'+mat+'.json'));j=json.loads(f.read_text(encoding='utf-8-sig'));colors=j['Parameters'].get('Colors',{});tex=j['Textures']
  if 'T_shell_BR' in tex:im=Image.open(next((P/'Ammo').rglob('T_shell_BR.png'))).convert('RGB')
  else:
   masks=next((v.split('.')[-1] for k,v in tex.items() if k=='URCS'),None);basecolor=colors.get('Color0000',{}).get('Hex','444444')[:6];rgb=np.asarray(bytes.fromhex(basecolor) and list(bytes.fromhex(basecolor)),dtype=float)
   path=next(src.rglob(str(masks)+'.png'),None)
   if path:
    mask=np.asarray(Image.open(path).convert('RGB').resize((512,512)),dtype=float)/255
    im=Image.fromarray(np.clip(rgb*(.84+.28*mask[:,:,0,None]),0,255).astype('uint8'))
   else:im=Image.new('RGB',(4,4),tuple(rgb.astype(int)))
  im.thumbnail((1024,1024));im.save(dest/(mat+'.png'))
if __name__=='__main__':build_textures(tmp/'Unity/Assets/JudgeMaterials')
