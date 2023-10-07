#!/bin/bash

# 检查参数数量
if [ "$#" -ne 1 ]; then
  echo "Please provide the target dir"
  exit 1
fi

# 获取路径
path="$1"

# 检查路径是否存在
if [ ! -d "$path" ]; then
  echo "Path not exist: $path"
  exit 1
fi

# 遍历路径下的所有scc*.html.gz文件
for file in "$path"/scc*.html.gz; do
  # 检查文件是否存在
  if [ ! -f "$file" ]; then
    echo "File not exist: $file"
    continue
  fi

  # 解压文件
  gunzip "$file"

  # 获取解压后的文件名（去掉.gz）
  new_file="${file%.gz}"

  # 重命名文件为.txt
  mv "$new_file" "${new_file%.html}.txt"
done

# 删除所有非scc开头的文件
for file in "$path"/*; do
  if [[ ! "$file" == "$path"/scc* ]]; then
    rm "$file"
  fi
done

echo "Finish!"

