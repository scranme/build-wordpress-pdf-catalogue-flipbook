# WordPress PDF 产品目录翻页插件生成器

[English](README.md) · [发布到 GitHub](PUBLISHING.md) · [测试说明](TESTING.md)

将产品目录 PDF 或排好顺序的页面图片，制作成**可直接上传到 WordPress 的翻页插件 ZIP**。
重点是完整的 WordPress 交付：不是只生成一个独立网页，再让使用者自己解决网站适配。

英文项目名：**WordPress PDF Catalogue Flipbook Builder**。  
Skill 调用名和 GitHub 仓库名：`build-wordpress-pdf-catalogue-flipbook`。

名称明确说明了用途：**产品目录 PDF／页面图片 → 书本翻页效果 → 可安装的 WordPress 插件**。
生成的插件默认名为 **WordPress PDF Catalogue Flipbook**；PDF 转换在本机完成，插件负责在网站展示画册。

这是独立编写的新 Skill。
不是 `create-photo-flipbook-ui` 的改名版，也不是其官方 WordPress 版本。
翻页引擎使用有许可证说明的 StPageFlip，其余构建与 WordPress 集成代码在本仓库中。

![WordPress 内的虚构产品画册示例](examples/preview-desktop.png)

以上为实际本地 WordPress 截图。[查看手机效果](examples/preview-mobile.png)。

## 主要功能

- 插件上传并启用即可用，不需要修改 `functions.php` 或替换主题。
- 原生 Product Flipbook 区块，也支持 `[product_flipbook catalogue="default"]` 短代码。
- 先展示封面，点击进入画册；电脑双页、手机单页，支持翻页、页码跳转、缩略图、搜索、放大、全屏和返回封面。
- 保持产品原图比例，不强制裁切；普通图、高清图、缩略图分开生成，按需加载临近页。
- 所有运行资源随插件打包，不依赖外部 CDN；错误有提示和重试，避免一直卡在 Loading。
- 包含代码、示例生成器、打包校验、自动化测试、GitHub Actions、中英文说明和许可证。

## 两种 ZIP 不要传错

| 文件 | 用途 |
| --- | --- |
| Skill 源码包 | 发布到 GitHub，或安装到 Codex 的 skills 目录。**不要上传到 WordPress 插件后台。** |
| 生成的 `wp-product-flipbook.zip` | 上传到 WordPress 的「插件 → 安装插件 → 上传插件」。包含运行代码和画册页面。 |

公开仓库只含虚构示例，不包含公司真实 PDF、商标或客户资料。你自己的目录和生成的公司插件应保存在仓库外。

## 在 Codex 使用

把本仓库文件夹命名为 `build-wordpress-pdf-catalogue-flipbook`，放进你的 Codex skills 目录，
确保该文件夹内直接包含 `SKILL.md`。重新载入技能列表或开启新会话后，可以说：

> 使用 $build-wordpress-pdf-catalogue-flipbook，把这份产品目录 PDF 做成 WordPress 插件。
> 保持比例，保证小字清晰，先显示封面再翻页。最后提供验证过的安装 ZIP。

它不会擅自上传 PDF、修改线上网站或公开发布 GitHub 仓库。

## 手动构建

本机需要 Python 3.10+，建议 3.12。网站服务器不需要 Python、Node.js 或构建工具。

```bash
python -m pip install -r requirements.txt
python scripts/build_wordpress_flipbook.py --input "产品目录.pdf" --output "新输出目录" --catalogue-title "产品目录"
python scripts/validate_wordpress_package.py "新输出目录/wp-product-flipbook.zip"
```

`--input` 也可指向按文件名排序的图片文件夹。每次构建使用新的输出文件夹，程序不会覆盖已有同名成果。
想先测试，可按英文 README 的命令生成原创的虚构示例。

## WordPress 中怎样使用

1. 后台「插件 → 安装插件 → 上传插件」，上传生成的 `wp-product-flipbook.zip` 并启用。
2. 新建或编辑页面，搜索 **Product Flipbook** 区块并选择目录；或添加「简码 / 短代码」区块，输入 `[product_flipbook catalogue="default"]`。
3. 预览前台，检查封面、翻页和手机显示；编辑器里的短代码输入框不会直接显示画册。
4. 发布页面，再通过 WordPress 导航编辑功能添加「产品目录」入口。插件不会擅自改菜单。

需要在页面内部打开，而不是弹窗，使用：

```text
[product_flipbook catalogue="default" mode="inline"]
```

## 清晰度与限制

默认页面长边为普通图 1600、高清图 2400、缩略图 320 像素。低清源图片不会通过放大变清晰。
PDF 中的一页默认视为书的一页：跨页排版、印刷拼版需要先确认拆分和顺序，不会盲目自动切半。
混合比例会补边而不是拉伸；奇数页默认补一张空白封底。

扫描 PDF 没有可提取的文字时，需要补充 SKU/标题元数据；本项目不包含 OCR。
搜索功能不能替代页面正文和产品详情页的 Google SEO。图片画册也不等于无障碍文本版本。

同一网站保持一个生成的插件包启用；可在同一页放多本画册实例。
如果需要多个不同目录，应合并到一个插件包的不同 catalogue 目录中，具体见 [WordPress 说明](references/wordpress.md)。
不包含后台 PDF 转换器、在线排版器或 WooCommerce 数据同步。
所有打包素材都是公开 URL，不能用它保护保密资料。

最低声明目标为 WordPress 6.2 / PHP 7.4；实际测过的版本与未测范围见 [测试记录](TESTING.md)。
主题、缓存插件、CDN 或页面构建器的组合仍需在你的测试站验证。

## GitHub 发布

1.0.1 版本更新了项目名、Skill 调用名和默认插件显示名。
为保持兼容，插件目录 `wp-product-flipbook`、主 PHP 文件、短代码 `product_flipbook`
和区块标识 `wpcf/product-flipbook` 保持不变，已有 WordPress 页面不需要修改。

按 [PUBLISHING.md](PUBLISHING.md) 创建自己的仓库，上传此目录的内容。
源码采用 MIT 许可证，第三方引擎保留原许可；用户产品资料不因此被授权公开。
不要把真实公司插件 ZIP、PDF、密钥、数据库或网站完整主题包一起发布。
