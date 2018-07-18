from django.shortcuts import render, get_object_or_404
from .models import Post, Category, Tag
from comments.forms import CommentForm
from django.views.generic import ListView, DetailView

import markdown

# Create your views here.

#index的类视图，用来代替index的视图函数， url中第二个参数指定视图函数，这里类视图.as_view()即可转换为函数
class IndexView(ListView):
    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'post_list'
    paginate_by = 4

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #父类生成的字典中已有 paginator、page_obj、is_paginated 三个模板变量
        paginator = context.get('paginator')
        page = context.get('page_obj')
        is_paginated = context.get('is_paginated')

        #调用方法获得新数据
        pagination_data = self.pagination_data(paginator, page, is_paginated)
        #更新这些数据到context中，是一个字典
        context.update(pagination_data)

        return context

    #新数据, 返回字典
    def pagination_data(self, paginator, page, is_paginated):
        if not is_paginated:
            return {}
        #定义当前页左边的页码[最多两个]
        left = []
        #定义当前页右边的页码[最多两个个]
        right = []
        #定义左边的省略号
        left_has_more = False
        #定义右边的省略号
        right_has_more = False
        #始终显示第一页，但若左边的页码包含第一页则不显示
        first = False
        #最后一页
        last = False
        #当前页
        page_number = page.number
        #总页数
        total_pages = paginator.num_pages
        #整个分页后的页码列表 如分四页则是 [1, 2, 3, 4]
        page_range = paginator.page_range

        if page_number == 1:
            #若请求的是第一页则不需要显示左边的
            #这里是取的当前页码后两个页码，其他数字也可以改
            right = page_range[page_number:page_number+2]

            #如果最右边的页码比（最后一页的页码-1）小则显示右边省略号
            #总页数也是最后一页的页码
            if right[-1] < total_pages -1:
                right_has_more = True

            #如果最右边的页码比（最后一页的页码）小则显示最后一页的页码
            if right[-1] < total_pages:
                last = True

        elif page_number == total_pages:
            #若请求的是最后一页，则不显示右边的
            #若(page_number - 3)为正数则就是该数，若为负数和0，就是0
            left = page_range[(page_number - 3) if (page_number - 3) > 0 else 0:page_number - 1]

            #右边省略号
            if left[0] > 2:
                left_has_more = True
            #显示第一页
            if left[0] > 1:
                first = True

        else:
            #两边都要
            left = page_range[(page_number - 3) if (page_number - 3) > 0 else 0:page_number - 1]
            right = page_range[page_number:page_number + 2]

            #省略号
            if left[0] > 2:
                left_has_more = True
            if right[-1] < total_pages -1:
                right_has_more = True

            #最前最后
            if left[0] > 1:
                first = True
            if right[-1] < total_pages:
                last = True

        data = {
            'left': left,
            'right': right,
            'left_has_more': left_has_more,
            'right_has_more': right_has_more,
            'first': first,
            'last': last,
        }
        return data

def index(request):
    #用objects.all()方法取出所有文章
    #用order_by()将取出的结果排序，根据方法里的参数来排
    post_list = Post.objects.all()
    return render(request, 'blog/index.html', context={
        'post_list': post_list,
    })

class PostDetailView(DetailView):
    # 这些属性的含义和 ListView 是一样的
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'

    def get(self, request, *args, **kwargs):
        #该方法目的在于每文章访问一次，增加一次阅读量
        #get方法返回了一个httpresponse实例
        #先调用父类方法， 才能使用self.object属性 这个属性是被访问的post实例
        response = super(PostDetailView, self).get(request, *args, **kwargs)

        self.object.increase_views()
        return response

    def get_object(self, queryset=None):
        post = super(PostDetailView, self).get_object(queryset=None)
        post.body = markdown.markdown(post.body,
                                      extensions=[
                                          'markdown.extensions.extra',
                                          'markdown.extensions.codehilite',
                                          'markdown.extensions.toc',
                                      ])
        return post

    def get_context_data(self, **kwargs):

        context = super(PostDetailView, self).get_context_data(**kwargs)
        form = CommentForm()
        comment_list = self.object.comment_set.all()
        context.update({
            'form': form,
            'comment_list': comment_list
        })
        return context


def detail(request, pk):
    # get_object_or_404()方法，传入的pk值若在Post存在时就返回object，若没有就返回404
    post = get_object_or_404(Post, pk=pk)

    # 阅读量加一
    post.increase_views()

    post.body = markdown.markdown(post.body,
                                  extensions=[
                                      'markdown.extensions.extra',
                                      'markdown.extensions.codehilite',
                                      'markdown.extensions.toc',
                                  ]
                                  )
    form = CommentForm()
    comment_list = post.comment_set.all()
    context = {'post': post,
               'form': form,
               'comment_list': comment_list
               }
    return render(request, 'blog/detail.html', context=context)


class ArchivesView(IndexView):

    def get_queryset(self):
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        return super(ArchivesView, self).get_queryset().filter(created_time__year=year,
                                                               created_time__month=month
                                                               )


def archives(request, year, month):
    post_list = Post.objects.filter(created_time__year=year,
                                    created_time__month=month
                                    )
    return render(request, 'blog/index.html', context={'post_list': post_list})


class CategoryView(IndexView):

    def get_queryset(self):
        # 这里取得cate 是一个Category对象（用get_object_or_404（）方法取），Post关联了Category对象
        # 上面的archives是用的Post的year和month属性，直接取
        cate = get_object_or_404(Category, pk=self.kwargs.get('pk'))
        return super(CategoryView, self).get_queryset().filter(category=cate)


def category(request, pk):
    cate = get_object_or_404(Category, pk=pk)
    post_list = Post.objects.filter(category=cate)
    return render(request, 'blog/index.html', context={'post_list': post_list})


class TagView(IndexView):

    def get_queryset(self):
        tag = get_object_or_404(Tag, pk=self.kwargs.get('pk'))
        return super(TagView, self).get_queryset().filter(tags=tag)
