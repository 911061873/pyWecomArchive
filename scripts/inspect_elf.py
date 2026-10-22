"""跨平台读取随包 ELF 的架构、依赖与所需符号版本。"""

from pathlib import Path

from elftools.elf.elffile import ELFFile

for path in Path("src/pywecomarchive/lib/linux").glob("*/*.so"):
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        dynamic = elf.get_section_by_name(".dynamic")
        needed = [tag.needed for tag in dynamic.iter_tags("DT_NEEDED")]
        versions = elf.get_section_by_name(".gnu.version_r")
        required = sorted(
            {
                aux.name
                for _, auxiliaries in versions.iter_versions()
                for aux in auxiliaries
            }
        )
        print(f"{path}: {elf.header['e_machine']}")
        print(f"依赖: {needed}")
        print(f"符号版本: {required}")
