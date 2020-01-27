"""
Bell collider script.

- Creates n joints at a radius r from the selected joint.
- each joint is rotated from the selected joint and will rotate on the same axis
- each joint will be driven via our angle driver
"""
import bm_bell_driver
import maya.cmds as cmds

reload(bm_bell_driver)


class BellCollider(object):
    def __init__(self,
                 min_angle=5,
                 max_angle=60,
                 radius_vector=None,
                 num_body_joints=3,
                 clapper=None,
                 name="BellCollider1",
                 out_axis="z",
                 down_axis="x",
                 sweep_axis="x",
                 driven_vector=None,
                 rotate_vector=None,
                 sweep_angle=360,
                 custom_joints=None):
        """Initialize our BellCollider object.

        :param min_angle: The minimum angle between the target and the bell vector where the value is 1
        :param max_angle: The maximum angle between the target and the bell vector where the value is 0
        :param radius_vector: The radius at which to create our bell joints
        :param num_body_joints: The number of toll joints to create
        :param clapper: An array representing the two objects that create our vector
        :param name: The name for our system
        :param out_axis: The axis to use for the radius "x","y",or "z"
        :param down_axis: The down axis of our bell joint
        :param sweep_axis: The axis to rotate around if we make joints via the sweep method
        :param driven_vector: The vector to go out when our sdk is triggered.
        :param rotate_vector: The rotation vector to use when our sdk is triggered.
        :param sweep_angle: The angle to sweep when creating our bell's body joints
        :param custom_joints: Custom joints to use instead of making joints with the sweep method.
        :type min_angle: float
        :type max_angle: float
        :type radius_vector: list
        :type num_body_joints: int
        :type clapper: list
        :type name: str
        :type out_axis: str
        :type down_axis: str
        :type sweep_axis: str
        :type driven_vector: list
        :type rotate_vector: list
        :type custom_joints: list
        """

        cmds.select(cl=1)

        if not clapper or len(clapper) != 2:
            return

        self.min_angle = min_angle
        self.max_angle = max_angle
        self.radius_vector = radius_vector
        self.num_body_joints = num_body_joints
        self.body_joints = []
        self.body_joint_bases = []
        self.body_joint_locs = []
        self.clapper = clapper
        self.name = name
        self.out_axis = out_axis
        self.out_axis_flip = 1

        if "-" in self.out_axis:
            self.out_axis_flip = -1
            self.out_axis = self.out_axis.replace("-", "")

        self.down_axis = down_axis
        self.sweep_axis = sweep_axis
        self.driven_vector = driven_vector
        self.rotate_vector = rotate_vector
        self.all_grp = None
        self.jnt_grp = None
        self.loc_grp = None
        self.mid_jnt = None
        self.sweep_angle = sweep_angle

        self.make_mid_joint()

        if not custom_joints:
            self.make_body_joints()
        else:
            self.body_joints = custom_joints

        self.setup_angle_driver()
        self.make_groups()
        self.make_attr()

    def make_mid_joint(self):
        """A mid joint is required so that all of our body joints can move out on a unified axis.

        :return: none
        """

        # create our mid joint
        self.mid_jnt = cmds.joint(name=self.name + "_mid_je")
        cmds.setAttr(self.mid_jnt + ".drawStyle", 2)
        # match it to the bell top
        cmds.matchTransform(self.mid_jnt, self.clapper[0])
        # freeze its transforms and bake it to it's joint orient
        cmds.makeIdentity(self.mid_jnt, apply=1, t=0, r=1, s=0, n=0, pn=1, jo=1)

    def make_body_joints(self):
        """Creates the "body" joints, which are the joints that go around the outside of the bell.

        :return: none
        """

        # create our body joints
        for i in range(0, self.num_body_joints):
            cmds.select(cl=1)
            body_joint_base = cmds.joint(name=self.name + "_bodyBase_%i_je" % (i + 1))
            cmds.matchTransform(body_joint_base, self.clapper[0])
            body_joint = cmds.joint(name=self.name + "_body_%i_jd" % (i + 1))
            cmds.matchTransform(body_joint, self.clapper[0])
            cmds.setAttr(body_joint_base + ".drawStyle", 2)

            cmds.parent(body_joint, self.mid_jnt, a=1)

            # go out from the position of the bell the length of our radius.
            cmds.xform(body_joint, t=self.radius_vector, os=1, r=1)

            # create a temporary group that will be used to rotate our joint around the mid joint
            tmp_grp = cmds.group(em=1)
            cmds.matchTransform(tmp_grp, self.clapper[0])
            cmds.parent(body_joint, tmp_grp, a=1)
            if self.num_body_joints != 1:
                cmds.setAttr(tmp_grp + ".r%s" % self.sweep_axis,
                             (i + 1) * (self.sweep_angle / float(self.num_body_joints)))
            cmds.parent(body_joint_base, self.mid_jnt, a=1)
            cmds.parent(body_joint, body_joint_base, a=1)
            cmds.delete(tmp_grp)

            # aims our joint's down axis to the clapper joint
            cmds.delete(cmds.aimConstraint(self.clapper[0], body_joint, aimVector=[1, 0, 0], upVector=[0, 1, 0], mo=0))
            # ToDo: Orient the roll axis of our bend joints
            cmds.makeIdentity(body_joint, apply=1, t=0, r=1, s=0, n=0, pn=1, jo=0)

            # orient our body base joint
            cmds.makeIdentity(body_joint_base, apply=1, t=0, r=1, s=0, n=0, pn=1, jo=0)
            cmds.joint(body_joint_base, e=1, oj="xyz", sao="yup", ch=1, zso=1)
            cmds.joint(body_joint, e=1, oj="none")

            self.body_joints.append(body_joint)
            self.body_joint_bases.append(body_joint_base)

    def setup_angle_driver(self):
        """Sets up a translation-based setup driven by a modification of our angle driver script.

        :return: none
        """

        # set up the angle driver for each joint
        for joint in self.body_joints:
            # create the target locator that represents the tail of the vector from the clapper to it
            target_loc = cmds.spaceLocator(name=self.name + "_%s_target_loc" % joint)[0]
            cmds.matchTransform(target_loc, joint, pos=1, rot=0)
            self.body_joint_locs.append(target_loc)

            bm_bell_driver.bell_driver_setup(vector_start=self.clapper[0],
                                             vector_end=self.clapper[1],
                                             target=target_loc,
                                             angle_min=self.min_angle,
                                             angle_max=self.max_angle,
                                             driven_node=joint,
                                             driven_vector=self.driven_vector,
                                             rotate_vector=self.rotate_vector)

    def make_groups(self):
        """Organizes our bell collider setup into groups.

        :return:
        """

        self.jnt_grp = cmds.group(self.mid_jnt, name=self.name + "_jnts")
        self.loc_grp = cmds.group(self.body_joint_locs, name=self.name + "_locs")
        self.all_grp = cmds.group(self.jnt_grp, self.loc_grp, name=self.name + "_all")

    def make_attr(self):
        """Creates Angle_Min and Angle_Max attributes on the top node of the group
        that will can be used to easily change the RemapValue nodes all at once.

        :return:
        """

        cmds.addAttr(self.all_grp, ln="Angle_Min", at="float", dv=self.min_angle, k=1)
        cmds.addAttr(self.all_grp, ln="Angle_Max", at="float", dv=self.max_angle, k=1)

        for jnt in self.body_joints:
            anim_node = cmds.listConnections(jnt + ".t%s" % self.out_axis)[0]
            remap_node = cmds.listConnections(anim_node + ".input")[0]
            cmds.connectAttr(self.all_grp + ".Angle_Min", remap_node + ".inputMin")
            cmds.connectAttr(self.all_grp + ".Angle_Max", remap_node + ".inputMax")
