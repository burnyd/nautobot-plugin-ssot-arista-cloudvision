import nautobot_ssot_aristacv.diffsync.cvutils as cvutils

from grpc import RpcError

from django.templatetags.static import static
from django.urls import reverse

from nautobot.extras.jobs import Job, BooleanVar
from nautobot.extras.models.tags import Tag
from nautobot.extras.models.customfields import CustomField

from nautobot_ssot.jobs.base import DataTarget, DataSource, DataMapping

from nautobot_ssot_aristacv.diffsync.tocv.cloudvision import CloudVision
from nautobot_ssot_aristacv.diffsync.tocv.nautobot import Nautobot

from nautobot_ssot_aristacv.diffsync.fromcv.cloudvision import CloudVision as C
from nautobot_ssot_aristacv.diffsync.fromcv.nautobot import Nautobot as N


class CloudVisionDataSource(DataSource, Job):
    debug = BooleanVar(description="Enable for more verbose debug logging")

    class Meta:
        name = "CloudVision"
        data_source = "Cloudvision"
        data_source_icon = static("nautobot_ssot_aristacv/cvp_logo.png")
        description = "Sync system tag data from CloudVision to Nautobot"

    @classmethod
    def data_mappings(cls):
        """List describing the data mappings involved in this DataSource."""
        return (
            DataMapping("topology_network_type", None, "Topology Network Type", None),
                DataMapping("mlag", None, "MLAG", None),
                DataMapping("mpls", None, "mpls", None),
                DataMapping("model", None, "Platform", reverse("dcim:platform_list")),
                DataMapping("systype", None, "systype", None),
                DataMapping("serialnumber", None, "Device Serial Number", None),
                DataMapping("pimbidir", None, "pimbidir", None),
                DataMapping("sflow", None, "sFlow", None),
                DataMapping("eostrain", None, "eosttain", None),
                DataMapping("tapagg", None, "tapagg", None),
                DataMapping("pim", None, "pim", None),
                DataMapping("bgp", None, "bgp", None),
                DataMapping("terminattr", None, "TerminAttr Version", None),
                DataMapping("ztp", None, "ztp", None),
                DataMapping("eos", None, "EOS Version", None),
            DataMapping("topology_type", None, "Topology Type", None),
        )

    def sync_data(self):
        self.log("Connecting to CloudVision")
        cvutils.connect()
        self.log("Loading data from CloudVision")
        cv = C()
        cv.load()
        self.log("Loading data from Nautobot")
        nb = N()
        nb.load()
        self.log("Performing diff between Cloudvision and Nautobot.")
        diff = nb.diff_from(cv)
        self.sync.diff = diff.dict()
        self.sync.save()
        self.log(diff.summary())
        if not self.kwargs["dry_run"]:
            self.log("Syncing to Nautbot")
            try:
                cv.sync_to(nb)
            except RpcError as e:
                self.log_failure("Sync failed.")
                raise e
            self.log_success(message="Sync complete.")
        cvutils.disconnect()

    def lookup_object(self, model_name, unique_id):
        if model_name == "cf":
            try:
                cf_name, value = unique_id.split("__")
                return CustomField.objects.get(name=f"{cf_name}")
            except CustomField.DoesNotExist:
                pass
        return None


class CloudVisionDataTarget(DataTarget, Job):
    debug = BooleanVar(description="Enable for more verbose debug logging")

    class Meta:
        name = "CloudVision"
        data_target = "CloudVision"
        data_target_icon = static("nautobot_ssot_aristacv/cvp_logo.png")
        description = "Sync tag data from Nautobot to CloudVision"

    @classmethod
    def data_mappings(cls):
        """List describing the data mappings involved in this DataTarget."""
        return (DataMapping("Tags", reverse("extras:tag_list"), "Device Tags", None),)

    def sync_data(self):
        self.log("Connecting to CloudVision")
        cvutils.connect()
        self.log("Loading data from CloudVision")
        cv = CloudVision(job=self)
        cv.load()
        self.log("Loading data from Nautobot")
        nb = Nautobot()
        nb.load()
        self.log("Performing diff between Nautobot and Cloudvision")
        diff = cv.diff_from(nb)
        self.sync.diff = diff.dict()
        self.sync.save()
        self.log(diff.summary())
        # if self.kwargs["debug"]:
        #     self.log_debug(diff_nb_cv.dict())
        if not self.kwargs["dry_run"]:
            self.log("Syncing to CloudVision")
            try:
                nb.sync_to(cv)
            except RpcError as e:
                self.log_failure("Sync failed.")
                raise e
            self.log_success(message="Sync complete")
        cvutils.disconnect()

    def lookup_object(self, model_name, unique_id):
        if model_name == "tag":
            try:
                tag_name, value = unique_id.split("__")
                return Tag.objects.get(name=f"{tag_name}:{value}")
            except Tag.DoesNotExist:
                pass
        return None


jobs = [CloudVisionDataSource, CloudVisionDataTarget]
