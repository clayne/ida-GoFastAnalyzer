import ida_pro
import ida_name
if ida_pro.IDA_SDK_VERSION < 850:
    import ida_struct
import ida_typeinf
from idc import BADADDR

from ida_kernwin import get_kernel_version

BYTE_SIZE = 8

IDA_MIN_GO_SUPPORT_VERSION = 8.1

GO_SUPPORTED = float(get_kernel_version()) >= IDA_MIN_GO_SUPPORT_VERSION

# list of register names representing the registers used in a go fastcall by their order
go_fast_convention = ["rax", "rbx", "rcx", "rdi", "rsi", "r8", "r9", "r10", "r11"]

runtime_morestack_functions = ["runtime.morestack_noctxt", "runtime.morestack"]

go_calling_convention = ida_typeinf.CM_CC_GOLANG if GO_SUPPORTED else ida_typeinf.CM_CC_MANUAL

def check_tinfo_zeroes(tinfo: ida_typeinf.tinfo_t) -> bool:
    for i in range(tinfo.get_udt_nmembers()):
        # find member
        member = ida_typeinf.udt_member_t()
        member.offset = i
        tinfo.find_udt_member(member, ida_typeinf.STRMEM_INDEX)

        # check zero_sized_members and fill them recursively
        if member.size == 0 or check_tinfo_zeroes(member.type):
            return True
    return False


def remove_tinfo_zeroes(tinfo: ida_typeinf.tinfo_t) -> bool:
    """
    Create a new structure without zero size members in it from the type info we receive
    """

    name = f"{tinfo.dstr()}_nozeroes"
    sid_or_tif = create_type(name)
    if ida_pro.IDA_SDK_VERSION < 850:
        struc = ida_struct.get_struc(sid_or_tif)
    else:
        struc_tif = sid_or_tif

    for i in range(tinfo.get_udt_nmembers()):
        # find member
        member = ida_typeinf.udt_member_t()
        member.offset = i
        tinfo.find_udt_member(member, ida_typeinf.STRMEM_INDEX)

        # check zero_sized members and fill them recursively
        if member.size == 0:
            continue

        if check_tinfo_zeroes(member.type):
            remove_tinfo_zeroes(member.type)
            member_type = ida_typeinf.tinfo_t()
            ida_typeinf.parse_decl(
                member_type, None, f"{member.type.dstr()}_nozeroes;", ida_typeinf.PT_SIL
            )
        # member has no zero sized members we can use it as is
        else:
            member_type = member.type

        # convert tinfo information to struct information
        name = ida_name.validate_name(member.name, ida_name.SN_NOCHECK)
        if ida_pro.IDA_SDK_VERSION < 850:
            member_size = member.size // BYTE_SIZE
            member_offset = member.offset // BYTE_SIZE

            ida_struct.add_struc_member(struc, name, member_offset, 0, None, member_size)
            mem = ida_struct.get_member(struc, member_offset)
            ida_struct.set_member_tinfo(struc, mem, member_offset, member_type, 0)
        else:
            member.name = name
            struc_tif.add_udm(member)

def tid_from_name(name: str) -> int:
    if ida_pro.IDA_SDK_VERSION < 850:
        return ida_struct.get_struc_id(name)
    else:
        return ida_typeinf.get_named_type_tid(name)

def create_type(name: str) -> int | ida_typeinf.tinfo_t:
    if ida_pro.IDA_SDK_VERSION < 850:
        sid = ida_struct.add_struc(BADADDR, struc_name)
        return sid
    else:
        udt = ida_typeinf.udt_type_data_t()
        udt.is_union = False
        tif = ida_typeinf.tinfo_t()
        tif.create_udt(udt)
        tif.set_named_type(None, name)
        return tif

