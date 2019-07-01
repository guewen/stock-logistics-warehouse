Sticky destination move creation

In a chain of operations (chained moves), changing the destination of a previous
move currently update the source of the following moves. We want that depending
on the picking type, instead of updating the next move’s source
location, we do create a new move and chain it back.

E.g.

* Chained moves are a -> b -> c

  * First operation requires a reach truck the second not
  * When processing a -> b, we change destination for d
  * New chained moves are: a -> d [done] -> b [new move] -> c
  * Therefore, a -> d and d -> b will be treated by reach truck whereas b -> c will not

This will allow operators to move goods where it makes sense for them at a given
moment, ensuring a next operation will be created to represent the original
operation. With this simple behavior you can allow people to change a planned
operation to react to a given situation without losing track of the next
operation to perform. That is especially true if some operation are performed by
reach truck and others are not.

