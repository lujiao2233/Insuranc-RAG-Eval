import categoryHierarchy from '@/assets/category_hierarchy.json'

interface CategoryNode {
  label: string
  value: string
  children?: CategoryNode[]
}

export function useCategoryHierarchy() {
  const categoryTree: CategoryNode[] = Object.entries(categoryHierarchy).map(([rootKey, level2Data]) => {
    const cleanKey = rootKey.replace(/^共享知识库-/, '')
    return {
      label: cleanKey,
      value: cleanKey,
      children: Object.entries(level2Data).map(([level2Key, level3Items]) => ({
        label: level2Key,
        value: level2Key,
        children: level3Items.map(item => ({
          label: item,
          value: item,
        })),
      })),
    }
  })

  const getCategoryPath = (values: string[]): string => {
    if (!values || values.length === 0) return ''
    return values.join('/')
  }

  return {
    categoryTree,
    getCategoryPath,
  }
}
