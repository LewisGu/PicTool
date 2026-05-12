import os
from PIL import Image


def batch_tiff_to_png(input_folder, output_folder=None, quality=95):
    """
    批量将 TIFF 文件转换为 PNG 格式

    参数:
        input_folder: 包含 TIFF 文件的文件夹路径
        output_folder: 输出文件夹路径（默认为 input_folder/png_output）
        quality: PNG 压缩质量（1-100，PNG 实际为无损，此参数影响某些情况下的处理）
    """

    # 设置输出文件夹
    if output_folder is None:
        output_folder = os.path.join(input_folder, "png_output")

    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)

    # 支持的 TIFF 扩展名
    tiff_extensions = ('.tiff', '.tif', '.TIFF', '.TIF')

    # 统计信息
    converted = 0
    failed = 0
    skipped = 0

    # 遍历文件夹中的所有文件
    for filename in os.listdir(input_folder):
        if filename.endswith(tiff_extensions):
            input_path = os.path.join(input_folder, filename)

            # 生成输出文件名
            base_name = os.path.splitext(filename)[0]
            output_filename = f"{base_name}.png"
            output_path = os.path.join(output_folder, output_filename)

            # 如果文件已存在，询问是否覆盖或跳过
            if os.path.exists(output_path):
                print(f"⚠️  跳过（已存在）: {filename}")
                skipped += 1
                continue

            try:
                # 打开 TIFF 文件
                with Image.open(input_path) as img:
                    # 处理多页 TIFF（保存每一页）
                    if hasattr(img, 'n_frames') and img.n_frames > 1:
                        print(f"📑 发现多页 TIFF: {filename}（共 {img.n_frames} 页）")

                        for page in range(img.n_frames):
                            img.seek(page)
                            page_output = os.path.join(
                                output_folder,
                                f"{base_name}_page{page + 1}.png"
                            )
                            img.save(page_output, 'PNG', optimize=True)
                            print(f"   ✓ 第 {page + 1} 页已保存")

                        converted += 1
                    else:
                        # 单页 TIFF 直接转换
                        img.save(output_path, 'PNG', optimize=True)
                        print(f"✅ 转换成功: {filename} → {output_filename}")
                        converted += 1

            except Exception as e:
                print(f"❌ 转换失败: {filename} - 错误: {str(e)}")
                failed += 1

    # 打印总结
    print("\n" + "=" * 50)
    print("📊 转换完成统计:")
    print(f"   成功: {converted}")
    print(f"   跳过: {skipped}")
    print(f"   失败: {failed}")
    print(f"   输出文件夹: {output_folder}")
    print("=" * 50)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 方法1: 直接修改下方路径
    # input_dir = r"你的TIFF文件夹路径"  # 例如: r"C:\Users\Name\Pictures\TIFF_Files"
    input_dir = r"D:\BaiduNetdiskDownload\顾鹏程 会员\01395"

    # 方法2: 使用当前脚本所在目录
    # input_dir = os.path.dirname(os.path.abspath(__file__))

    # 运行转换
    batch_tiff_to_png(input_dir)