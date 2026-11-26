import bpy,numpy as np
from pathlib import Path
s=bpy.context.scene
def arm(tag):return next(o for o in s.objects if tag in o.name and o.type=='ARMATURE')
hands=arm('Gloves');body=arm('Body_LowerReceiver');mag=arm('Mag_Standard');loader=arm('SpeedLoader')
d={}
for i in range(114):
 s.frame_set(i)
 for o,bs in [(hands,[b.name for b in hands.pose.bones]),(body,['Body']),(mag,['Mag','Hinge','Ejector']),(loader,['SpeedLoader'])]:
  for b in bs:d.setdefault(b,[]).append(np.array(o.matrix_world@o.pose.bones[b].matrix))
np.savez('E:/Temp/Justicar-RSh/pd3reload.npz',**d)
